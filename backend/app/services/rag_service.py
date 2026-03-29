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
    section_3_real_case_example: str = Field(description="3️⃣ 현실 적용 예시 및 관련 판례 (제공된 [관련 판례/재결례 정보]가 있다면 반드시 이를 요약해서 포함할 것. 사건명과 판결요지를 명시)")
    section_4_caution: str = Field(description="4️⃣ 주의사항 (예외 상황, 오해하기 쉬운 부분, 분쟁 가능성)")
    section_5_counseling_recommendation: str = Field(description="5️⃣ 법률 상담 권장 여부 (필요시 '정확한 판단은 노무사/변호사 상담이 필요합니다.' 명시)")
    section_6_suggested_followups: list[str] = Field(description="6️⃣ 추천 후속 질문 3가지 (사용자의 현재 상황에서 궁금해할 만한 이어지는 질문)")

class LegalFactChecker:
    """
    RAG(Retrieval-Augmented Generation) 기반의 핵심 팩트체크 클래스.
    벡터 DB를 조회해 관련 법령을 찾고 LLM을 통해 FactCheckResult를 도출합니다.
    """
    def __init__(self):
        """
        LegalFactChecker의 생성자입니다.
        벡터 스토어 경로, 임베딩 모델(OpenAI), 주 판단용(Main) LLM, JSON 출력 파서,
        그리고 검색된 문서 문맥을 압축/요약하기 위한 ContextCompressor를 초기화합니다.
        """
        settings = get_settings()
        self.embeddings = OpenAIEmbeddings()
        self.vector_store_path = settings.VECTOR_STORE_PATH
        self.vector_store = None
        self.llm = get_main_llm()
        self.parser = JsonOutputParser(pydantic_object=FactCheckResult)
        self.compressor = ContextCompressor()

    def initialize_vector_store(self):
        """
        설정된 경로(VECTOR_STORE_PATH)에 존재하는 로컬 Chroma 오픈소스 벡터 DB를 
        동기적으로 로드하여 팩트체크 검색(Retriever)에 사용할 준비를 마칩니다.
        """
        self.vector_store = Chroma(
            persist_directory=self.vector_store_path,
            embedding_function=self.embeddings
        )

    async def add_revisions(self, revisions_data: list[dict]):
        """
        DB에 저장된 법령 개정안이나 조문(LawArticleRevision) 데이터를
        문서 변환을 거쳐 벡터 스토어에 삽입(Add) 및 임베딩 처리합니다.

        Args:
            revisions_data (list[dict]): 추가 또는 갱신할 법령/조문 메타데이터 및 텍스트 콘텐츠 리스트
        """
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
        """
        이전 채팅 내역과 부가적인 플러그인 문맥을 참고하여 벡터 DB에서 관련된 법령/판례를 조회하고,
        LLM을 통해 구조화된 형태(FactCheckResult)로 팩트체크 및 검증 결과를 최종 도출합니다.

        Args:
            query (str): 팩트체크 대상이 되는 사용자 질문 또는 보완된 검색 쿼리
            chat_history (list): 사용자와의 이전 대화 내역 (Human/AI 역할 모델 컨버팅 포함)
            plugin_context (str, optional): Agent나 Vision 판단 등 외부 플러그인에서 생성되어 검색 정확도를 높여주는 추가 문맥(텍스트). Defaults to "".

        Returns:
            dict: AI가 판정한 팩트체크 포맷 결과(result), 참고 조문 출처들의 리스트(sources), 참고 법 조항 메타데이터(revision_ids) 요소
        """
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
        except json.JSONDecodeError:
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
