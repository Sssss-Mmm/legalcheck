from pydantic import BaseModel, Field
from typing import List
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
import json

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

class OutputValidator:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0) # Use faster/cheaper model for simple correction
        
    async def validate_and_correct(self, result: dict) -> dict:
        """
        AI가 생성한 답변(FactCheckResult 형태)을 검사하여
        단정적 표현(100% 이긴다), 감정적 위로, 잘못된 법률 용어 직역이 있는지 확인 후
        문제가 있으면 안전하고 중립적인 언어로 "교정"하여 반환합니다.
        """
        
        system_prompt = """당신은 법률 팩트체커 시스템의 '최종 출력 검증기(Output Hook)'입니다.
다음은 AI가 작성한 5단계 법률 팩트체크 초안입니다.

**검사 및 교정 규칙:**
1. **단정적 예측 불가**: "100% 승소합니다", "무조건 이길 수 있습니다", "확실합니다", "불법입니다(법원 판결 전)" 와 같은 단정적인 소송 조언이나 결과를 예단하는 표현이 있다면, "승소/인정될 가능성이 있습니다", "위법 소지가 있습니다", "구체적인 판단은 전문가 상담이 필요합니다" 등으로 **교정**하세요.
2. **법률용어 순화**: 불필요한 라틴어 법률 용어나 너무 어려운 전문 용어가 설명 없이 쓰였다면 쉬운 한국어로 **교정**하세요.
3. **감정적 동요 제거**: "너무 억울하시겠습니다", "힘내세요" 등 감정적 위로나 공감이 섞인 문장이 있다면 해당 부분을 **삭제**하세요. (사실 확인만 남기세요)
4. **구조 유지**: 입력된 5단계 JSON 구조(키 값)를 정확히 유지해야 합니다.
5. **문제 없음 통과**: 위의 규칙에 위반되는 사항이 없다면, 원본 텍스트를 그대로 유지하세요.

반드시 원본과 동일한 JSON 키를 가진 순수 JSON 객체로 응답하세요. Markdown 블록(```json 등)없이 순수 JSON 문자열만 반환하세요.
"""
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", "다음 초안을 검증 및 교정하세요.\n\n{draft}")
        ])
        
        # We enforce JSON output directly by prompt
        chain = prompt | self.llm
        
        try:
            draft_json = json.dumps(result, ensure_ascii=False)
            response = await chain.ainvoke({
                "draft": draft_json
            })
            
            # Parse the response (handling potential markdown blocks just in case)
            corrected_text = response.content.strip()
            if corrected_text.startswith("```json"):
                corrected_text = corrected_text[7:-3].strip()
            elif corrected_text.startswith("```"):
                corrected_text = corrected_text[3:-3].strip()
                
            corrected_json = json.loads(corrected_text)
            
            # Ensure the verdict field wasn't dropped
            if "verdict" not in corrected_json and "verdict" in result:
                corrected_json["verdict"] = result["verdict"]
                
            return corrected_json
            
        except Exception as e:
            print(f"Output Validation failed: {e}")
            # Fallback to the original output if validation chain fails
            return result
