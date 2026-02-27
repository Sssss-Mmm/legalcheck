from pydantic import BaseModel, Field
from typing import List
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

class IntentResult(BaseModel):
    intent: str = Field(description="사용자 질문의 핵심 의도 (예: 부당해고 가능성, 체불임금 계산 등)")
    law_domain: str = Field(description="적용 가능한 법 영역 (예: 근로기준법, 산업안전보건법, 알 수 없음 등)")
    keywords: List[str] = Field(description="질문에서 추출한 핵심 법률/사실 키워드 목록")
    is_legal_question: bool = Field(description="이 질문이 법률 지식을 요구하는 질문인지 여부 (단순 인사말, 무관한 질문은 false)")
    is_counseling_request: bool = Field(description="단순 정보 요청이 아닌, 구체적인 상황에 대한 법률 상담 요청인지 여부")

class InputAnalyzer:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0)
        self.parser = JsonOutputParser(pydantic_object=IntentResult)

    async def analyze_query(self, query: str) -> dict:
        system_prompt = """당신은 법률 팩트체커 시스템의 '첫 번째 단계(Input Hook)'를 담당하는 분석기입니다.
사용자의 입력(질문, 주장, 하소연 등)을 받아서 아래의 규칙에 따라 철저히 분석하고 구조화된 데이터를 반환해야 합니다.

**역할 및 규칙:**
1. **감정적 표현 제거**: 사용자가 아무리 감정적으로 글을 썼더라도, 사실 관계와 핵심 질문만 추출하세요.
2. **질문 분류**: 이것이 법률 기반의 팩트체크가 필요한 질문인지, 아니면 단순한 인사말/장난인지 구분하세요 (`is_legal_question`).
3. **요청 성격 파악**: 일반적인 법과 규정에 대한 '정보 요청'인지, 자신의 특수한 상황을 해결해 달라는 '상담 요청'인지 파악하세요 (`is_counseling_request`).
4. **적용 법 영역**: 질문 내용이 어떤 법률 분야(예: 근로기준법, 남녀고용평등법 등)와 연관되는지 판단하여 기재하세요. 확실하지 않으면 '알 수 없음'으로 기재하세요.
5. **키워드 추출**: 시스템이 법령 DB나 판례를 검색할 때 사용할 수 있는 핵심 명사형 키워드를 2~5개 추출하세요.

반드시 아래의 지시사항에 따라 JSON 형태로만 응답하세요.

{format_instructions}
"""
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", "{query}")
        ])

        chain = prompt | self.llm | self.parser
        
        try:
            result = await chain.ainvoke({
                "query": query,
                "format_instructions": self.parser.get_format_instructions()
            })
            return result
        except Exception as e:
            # Fallback in case of parsing error
            return {
                "intent": "분석 오류",
                "law_domain": "알 수 없음",
                "keywords": [],
                "is_legal_question": True,
                "is_counseling_request": False
            }
