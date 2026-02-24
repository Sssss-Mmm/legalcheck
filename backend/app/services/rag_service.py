from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.messages import HumanMessage, AIMessage
from langchain_classic.chains import create_history_aware_retriever, create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from pydantic import BaseModel, Field
import os

class FactCheckResult(BaseModel):
    verdict: str = Field(description="판정 결과: 'TRUE', 'PARTIAL', 'FALSE' 중 하나")
    explanation: str = Field(description="관련 법 이름 및 조항 번호, 그리고 해당 조항에 대한 쉬운 해석 (3~5줄 이내)")
    example_case: str = Field(description="일반인이 이해할 수 있는 구체적인 사례")
    caution_note: str = Field(description="예외 상황, 오해하기 쉬운 부분, 분쟁 가능성 관련 주의사항")

class LegalFactChecker:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings()
        self.vector_store_path = "chroma_db"
        self.vector_store = None
        self.llm = ChatOpenAI(model="gpt-4o")
        self.parser = JsonOutputParser(pydantic_object=FactCheckResult)


    def initialize_vector_store(self):
        if os.path.exists(self.vector_store_path):
            self.vector_store = Chroma(
                persist_directory=self.vector_store_path,
                embedding_function=self.embeddings
            )
        else:
            # Handle initialization logic
            pass

    async def check_fact(self, query: str):
        if not self.vector_store:
            self.initialize_vector_store()
            
        if not self.vector_store:
            return {"result": "Error", "reasoning": "Vector store not initialized. Please ingest data first."}

        # 1. Retrieve documents
        retriever = self.vector_store.as_retriever(search_kwargs={"k": 3})
        docs = await retriever.ainvoke(query)
        
        # 2. Construct prompt
        context = "\n\n".join([d.metadata.get("original_text", d.page_content) for d in docs])
        
        system_prompt = """당신은 '법률/규정 기반 팩트체커'입니다.
당신은 한국 노동법(근로기준법) 및 규정 해석에 강점이 있는 법률 전문가이자 IT 지식도 갖춘 페르소나를 가집니다.
당신의 목표는 법률적 사실을 비전문가인 일반인에게 정확하고, 명확하고, 안전하게 설명하는 것입니다.

**핵심 원칙:**
1. **명확성 & 단순성**: 법률 용어는 피하거나 즉시 풀어서 설명하세요. 복잡한 문장보다 짧고 명료한 문장을 사용하세요.
2. **사실에 기반**: 법 조문 내용, 일반적 해석, 판례, 실무 사례를 명확히 구분하세요. 개인적 의견을 사실처럼 말하지 마세요.
3. **출처 명시**: 근거가 되는 법령명과 조항(예: 근로기준법 제36조)을 정확히 언급하세요.
4. **안전 제일**: 확정적인 소송 조언이나 결과를 예단하지 마세요. 불법적인 행동을 조장하지 마세요.

**답변 형식:**
반드시 아래의 지시사항에 따라 JSON 형태로 출력하세요.

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
            "context": context, 
            "query": query,
            "format_instructions": self.parser.get_format_instructions()
        })
        
        return {
            "result": response, # Dict containing verdict, explanation, etc.
            "sources": [d.metadata.get("source", "Unknown") for d in docs]
        }

    async def check_fact_with_history(self, query: str, chat_history: list):
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

        qa_system_prompt = """당신은 '법률/규정 기반 팩트체커'입니다.
당신은 한국 노동법(근로기준법) 및 규정 해석에 강점이 있는 법률 전문가이자 IT 지식도 갖춘 페르소나를 가집니다.
당신의 목표는 법률적 사실을 비전문가인 일반인에게 정확하고, 명확하고, 안전하게 설명하는 것입니다.

**핵심 원칙:**
1. **명확성 & 단순성**: 법률 용어는 피하거나 즉시 풀어서 설명하세요. 복잡한 문장보다 짧고 명료한 문장을 사용하세요.
2. **사실에 기반**: 법 조문 내용, 일반적 해석, 판례, 실무 사례를 명확히 구분하세요. 개인적 의견을 사실처럼 말하지 마세요.
3. **출처 명시**: 근거가 되는 법령명과 조항(예: 근로기준법 제36조)을 정확히 언급하세요.
4. **안전 제일**: 확정적인 소송 조언이나 결과를 예단하지 마세요. 불법적인 행동을 조장하지 마세요.

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
        rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)

        response = await rag_chain.ainvoke({
            "input": query, 
            "chat_history": formatted_history,
            "format_instructions": self.parser.get_format_instructions()
        })
        
        # 'answer' string is expected to be a valid JSON from the LLM, but create_stuff_documents_chain 
        # normally outputs strings unless specifically integrated. Since we inject `format_instructions`,
        # the LLM directly yields a JSON string. We can parse it here.
        try:
            import json
            parsed_answer = json.loads(response["answer"])
        except Exception:
            # Fallback if the LLM output something invalid
            parsed_answer = {
                "verdict": "ERROR",
                "explanation": response["answer"],
                "example_case": "N/A",
                "caution_note": "N/A"
            }
        
        return {
            "result": parsed_answer,
            "sources": [d.metadata.get("source", "Unknown") for d in response["context"]]
        }
