from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.messages import HumanMessage, AIMessage
from langchain_classic.chains import create_history_aware_retriever
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from pydantic import BaseModel, Field
import json
import logging

from app.core.llm import get_main_llm
from app.core.config import get_settings
from app.services.context_service import ContextCompressor
from app.services.prompts import FACT_CHECK_SYSTEM_PROMPT, CONTEXTUALIZE_Q_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

class FactCheckResult(BaseModel):
    verdict: str = Field(description="판정 결과: '사실', '일부 사실', '사실 아님', '추가 판단 필요' 중 하나")
    section_1_summary: str = Field(description="1️⃣ 핵심 요약 (3~5줄 이내)")
    section_2_law_explanation: str = Field(description="2️⃣ 법 조문 기준 설명 (관련 법 이름, 조항 번호, 쉬운 해석)")
    section_3_real_case_example: str = Field(description="3️⃣ 현실 적용 예시 (일반인이 이해할 수 있는 사례)")
    section_4_caution: str = Field(description="4️⃣ 주의사항 (예외 상황, 오해하기 쉬운 부분, 분쟁 가능성)")
    section_5_counseling_recommendation: str = Field(description="5️⃣ 법률 상담 권장 여부 (필요시 '정확한 판단은 노무사/변호사 상담이 필요합니다.' 명시)")
    section_6_suggested_followups: list[str] = Field(description="6️⃣ 추천 후속 질문 3가지 (사용자의 현재 상황에서 궁금해할 만한 이어지는 질문)")

class LegalFactChecker:
    def __init__(self):
        settings = get_settings()
        self.embeddings = OpenAIEmbeddings()
        self.vector_store_path = settings.VECTOR_STORE_PATH
        self.vector_store = None
        self.llm = get_main_llm()
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

        contextualize_q_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", CONTEXTUALIZE_Q_SYSTEM_PROMPT),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ]
        )
        
        history_aware_retriever = create_history_aware_retriever(
            self.llm, retriever, contextualize_q_prompt
        )

        qa_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", FACT_CHECK_SYSTEM_PROMPT),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ]
        ).partial(format_instructions=self.parser.get_format_instructions())
        
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
        })
        
        try:
            parsed_answer = json.loads(answer_response)
        except Exception:
            parsed_answer = {
                "verdict": "ERROR",
                "section_1_summary": str(answer_response),
                "section_2_law_explanation": "응답 처리 오류 발생",
                "section_3_real_case_example": "N/A",
                "section_4_caution": "N/A",
                "section_5_counseling_recommendation": "N/A",
                "section_6_suggested_followups": []
            }
        
        return {
            "result": parsed_answer,
            "sources": [d.metadata.get("source", "Unknown") for d in docs],
            "revision_ids": [d.metadata.get("revision_id") for d in docs if "revision_id" in d.metadata]
        }
