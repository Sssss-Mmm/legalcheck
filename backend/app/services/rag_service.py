from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.messages import HumanMessage, AIMessage
from langchain_classic.chains import create_history_aware_retriever, create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from pydantic import BaseModel, Field
import os
from app.services.context_service import ContextCompressor

class FactCheckResult(BaseModel):
    verdict: str = Field(description="판정 결과: '사실', '일부 사실', '사실 아님', '추가 판단 필요' 중 하나")
    section_1_summary: str = Field(description="1️⃣ 핵심 요약 (3~5줄 이내)")
    section_2_law_explanation: str = Field(description="2️⃣ 법 조문 기준 설명 (관련 법 이름, 조항 번호, 쉬운 해석)")
    section_3_real_case_example: str = Field(description="3️⃣ 현실 적용 예시 (일반인이 이해할 수 있는 사례)")
    section_4_caution: str = Field(description="4️⃣ 주의사항 (예외 상황, 오해하기 쉬운 부분, 분쟁 가능성)")
    section_5_counseling_recommendation: str = Field(description="5️⃣ 법률 상담 권장 여부 (필요시 '정확한 판단은 노무사/변호사 상담이 필요합니다.' 명시)")

class LegalFactChecker:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings()
        self.vector_store_path = "chroma_db"
        self.vector_store = None
        self.llm = ChatOpenAI(model="gpt-4o")
        self.parser = JsonOutputParser(pydantic_object=FactCheckResult)
        self.compressor = ContextCompressor()


    def initialize_vector_store(self):
        self.vector_store = Chroma(
            persist_directory=self.vector_store_path,
            embedding_function=self.embeddings
        )

    async def add_revisions(self, revisions_data: list[dict]):
        if not self.vector_store:
            self.initialize_vector_store()
            
        from langchain_core.documents import Document
        
        docs = []
        for rev in revisions_data:
            metadata = {
                "law_id": rev.get("law_id"),
                "article_id": rev.get("article_id"),
                "revision_id": rev.get("revision_id"),
                "source": f"{rev.get('law_name', '법')} {rev.get('article_number', '조항')}"
            }
            docs.append(Document(page_content=rev["content"], metadata=metadata))
            
        if docs:
            self.vector_store.add_documents(docs)

    async def check_fact(self, query: str, plugin_context: str = ""):
        if not self.vector_store:
            self.initialize_vector_store()
            
        if not self.vector_store:
            return {"result": "Error", "reasoning": "Vector store not initialized. Please ingest data first."}

        # 1. Retrieve documents
        retriever = self.vector_store.as_retriever(search_kwargs={"k": 3})
        docs = await retriever.ainvoke(query)
        
        # 2. Compress context
        compressed_context = await self.compressor.compress_documents(query, docs)
        
        if plugin_context:
            compressed_context += f"\n\n{plugin_context}"
        
        system_prompt = """당신은 한국 노동법(근로기준법) 및 규정 해석에 강점이 있는 IT 법률 팩트체커입니다.
당신의 목표는 법률적 사실을 비전문가인 일반인에게 정확하고, 명확하고, 안전하게 설명하는 것입니다.

**Explanation Structure (MANDATORY)**
Every explanation must follow exactly this JSON structure mapped by the instructions:
1️⃣ 핵심 요약 (3~5줄 이내)
2️⃣ 법 조문 기준 설명 (관련 법 이름, 조항 번호, 쉬운 해석)
3️⃣ 현실 적용 예시 (일반인이 이해할 수 있는 사례)
4️⃣ 주의사항 (예외 상황, 오해하기 쉬운 부분, 분쟁 가능성)
5️⃣ 법률 상담 권장 여부 (실제 소송/분쟁 가능성이 있다면 "정확한 판단은 노무사/변호사 상담이 필요합니다." 명시)

**Language & Tone Rules:**
- Clear. Simple. Accurate. Calm. No legal jargon without explanation.
- Avoid Latin legal terms and unnecessary jargon. Keep sentences short.
- Never give definitive litigation advice. Never predict court outcome with certainty.
- Always clarify that information is for general guidance.
- 감정적 위로 금지. 사실 확인과 정보 제공에만 집중하세요.

**답변 형식:**
반드시 아래의 지시사항에 따라 JSON 형태로만 출력하세요.

{format_instructions}

**Context (법률/규정 데이터):**
{context}

사용자의 주장에 대해 위 Context를 근거로 사실 여부를 판정하고 결과를 JSON으로 작성해 주세요.
"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", "{query}")
        ])
        
        
        # 3. Call LLM
        chain = prompt | self.llm | self.parser
        response = await chain.ainvoke({
            "context": compressed_context, 
            "query": query,
            "format_instructions": self.parser.get_format_instructions()
        })
        
        return {
            "result": response, # Dict containing verdict, explanation, etc.
            "sources": [d.metadata.get("source", "Unknown") for d in docs],
            "revision_ids": [d.metadata.get("revision_id") for d in docs if "revision_id" in d.metadata]
        }

    async def check_fact_with_history(self, query: str, chat_history: list, plugin_context: str = ""):
        if not self.vector_store:
            self.initialize_vector_store()
            
        if not self.vector_store:
            return {"result": "Error", "reasoning": "Vector store not initialized. Please ingest data first."}

        formatted_history = []
        for msg in chat_history:
            if msg["role"] == "user":
                formatted_history.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "ai":
                formatted_history.append(AIMessage(content=msg["content"]))

        retriever = self.vector_store.as_retriever(search_kwargs={"k": 3})

        contextualize_q_system_prompt = (
            "Given a chat history and the latest user question "
            "which might reference context in the chat history, "
            "formulate a standalone question which can be understood "
            "without the chat history. Do NOT answer the question, "
            "just reformulate it if needed and otherwise return it as is."
        )
        contextualize_q_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", contextualize_q_system_prompt),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ]
        )
        
        history_aware_retriever = create_history_aware_retriever(
            self.llm, retriever, contextualize_q_prompt
        )

        qa_system_prompt = """당신은 한국 노동법(근로기준법) 및 규정 해석에 강점이 있는 IT 법률 팩트체커입니다.
당신의 목표는 법률적 사실을 비전문가인 일반인에게 정확하고, 명확하고, 안전하게 설명하는 것입니다.

**Explanation Structure (MANDATORY)**
Every explanation must follow exactly this JSON structure mapped by the instructions:
1️⃣ 핵심 요약 (3~5줄 이내)
2️⃣ 법 조문 기준 설명 (관련 법 이름, 조항 번호, 쉬운 해석)
3️⃣ 현실 적용 예시 (일반인이 이해할 수 있는 사례)
4️⃣ 주의사항 (예외 상황, 오해하기 쉬운 부분, 분쟁 가능성)
5️⃣ 법률 상담 권장 여부 (실제 소송/분쟁 가능성이 있다면 "정확한 판단은 노무사/변호사 상담이 필요합니다." 명시)

**Language & Tone Rules:**
- Clear. Simple. Accurate. Calm. No legal jargon without explanation.
- Avoid Latin legal terms and unnecessary jargon. Keep sentences short.
- Never give definitive litigation advice. Never predict court outcome with certainty.
- Always clarify that information is for general guidance.
- 감정적 위로 금지. 사실 확인과 정보 제공에만 집중하세요.

**답변 형식:**
반드시 아래의 지시사항에 따라 JSON 형태로 출력하세요. 출력 언어는 한국어입니다.

{format_instructions}

**Context (법률/규정 데이터):**
{context}

위 Context를 바탕으로 사용자의 최신 주장에 대한 사실 여부를 판정하고 JSON으로 답변을 작성해 주세요.
"""

        qa_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", qa_system_prompt),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ]
        )
        
        question_answer_chain = create_stuff_documents_chain(self.llm, qa_prompt)

        # Retrieve documents manually
        docs = await history_aware_retriever.ainvoke({"input": query, "chat_history": formatted_history})
        
        # Compress context
        compressed_context = await self.compressor.compress_documents(query, docs)
        
        if plugin_context:
            compressed_context += f"\n\n{plugin_context}"
            
        from langchain_core.documents import Document
        compressed_doc = Document(page_content=compressed_context)

        answer_response = await question_answer_chain.ainvoke({
            "input": query, 
            "chat_history": formatted_history,
            "context": [compressed_doc],
            "format_instructions": self.parser.get_format_instructions()
        })
        
        # 'answer' string is expected to be a valid JSON from the LLM, but create_stuff_documents_chain 
        # normally outputs strings unless specifically integrated. Since we inject `format_instructions`,
        # the LLM directly yields a JSON string. We can parse it here.
        try:
            import json
            parsed_answer = json.loads(answer_response)
        except Exception:
            # Fallback if the LLM output something invalid
            parsed_answer = {
                "verdict": "ERROR",
                "section_1_summary": str(answer_response),
                "section_2_law_explanation": "응답 처리 오류 발생",
                "section_3_real_case_example": "N/A",
                "section_4_caution": "N/A",
                "section_5_counseling_recommendation": "N/A"
            }
        
        return {
            "result": parsed_answer,
            "sources": [d.metadata.get("source", "Unknown") for d in docs],
            "revision_ids": [d.metadata.get("revision_id") for d in docs if "revision_id" in d.metadata]
        }
