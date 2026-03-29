from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import logging

from app.core.llm import get_mini_llm

logger = logging.getLogger(__name__)

class ContextCompressor:
    """
    RAG 검색된 원문 컨텍스트에서 사용자 질문과 관련된 필수 정보만을 압축하여 반환하는 컴프레서(Compressor)입니다.
    """
    def __init__(self):
        """
        ContextCompressor의 생성자입니다.
        비용 효율성을 고려하여 요약 및 발췌 목적의 경량(Mini) LLM을 초기화하고,
        결과물을 문자열(str)로 출력하기 위한 파서를 설정합니다.
        """
        self.llm = get_mini_llm()
        self.parser = StrOutputParser()

    async def compress_documents(self, query: str, docs: list) -> str:
        """
        RAG 파이프라인에서 검색된 방대한 개별 문서 텍스트들에서,
        사용자의 질문과 직접적으로 관련된 핵심 내용(조건, 예외사항 등)만 발췌하여
        압축된 형태의 단일 컨텍스트 문자열을 생성합니다.

        Args:
            query (str): 사용자의 원본 팩트체크 질문
            docs (list): 벡터 스토어나 법령 DB에서 검색되어 반환된 문서(Document) 객체 리스트

        Returns:
            str: 시스템 프롬프트 규칙에 따라 핵심 내용만 개조식으로 요약된 문자열
        """
        if not docs:
            return ""
            
        raw_context = "\n\n".join([f"--- 문서 (출처: {d.metadata.get('source', '알 수 없음')}) ---\n{d.page_content}" for d in docs])
        
        system_prompt = """당신은 법률/규정 팩트체크 시스템을 위한 'Context 압축기'입니다.
아래 제공된 [검색된 문서(법 조문, 판례 등)] 원문에서, 
사용자의 [질문]에 답변하는 데 꼭 필요한 핵심 규칙/조건/제외사항만 선별하여 간결하게 발췌 및 요약하세요.

**압축 규칙:**
1. 사용자의 질문과 무관한 법 조항이나 판례 내용은 과감히 버리세요.
2. 각 문서의 출처(조문 번호, 판례 번호 등)를 명시하면서, 핵심 내용을 3~5줄 이내의 개조식(Bullet points)으로 정리하세요.
3. 질문에서 답변을 내릴 수 없는 내용이라도, 질문과 연관된 조문이 있다면 그 조항의 원칙만 간략히 요약하세요.
4. 당신의 개인적인 해석이나 창작을 더하지 마세요. 문서에 있는 사실 그대로 발췌하되 길이만 줄이세요.
5. "이 조항에 따르면..." 같은 불필요한 서술어를 빼고 명사형이나 간결한 문장형태로 쓰세요.
"""
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", "[질문]: {query}\n\n[검색된 문서]:\n{raw_context}\n\n위 문서를 기반으로 필수 정보만 압축해 주세요.")
        ])
        
        chain = prompt | self.llm | self.parser
        
        try:
            compressed_context = await chain.ainvoke({
                "query": query,
                "raw_context": raw_context
            })
            return compressed_context
        except Exception as e:
            logger.error(f"Context compression failed: {e}")
            # Fallback to the raw context format if LLM fails
            return raw_context
