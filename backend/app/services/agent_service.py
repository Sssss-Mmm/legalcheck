from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from app.services.hook_service import IntentResult

class AgentAction(BaseModel):
    requires_law_db_search: bool = Field(description="관련 법 조문을 데이터베이스에서 찾아보아야 하는가?")
    requires_precedent_search: bool = Field(description="과거의 유사한 사례나 실제 판례(법원 판결)를 찾아보아야 하는가?")
    requires_calculator: bool = Field(description="해고예고수당, 퇴직금, 주휴수당, 연차수당 등 특정 금전적 계산이 필요한가?")
    requires_clarification: bool = Field(description="사용자의 질문이 너무 모호하거나 사실관계 판단을 위한 핵심 정보가 누락되어 되물어야 하는가?")
    reasoning: str = Field(description="위 도구들의 사용 필요성 여부를 결정한 논리적인 이유")

class RoutingAgent:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0)
        self.parser = JsonOutputParser(pydantic_object=AgentAction)

    async def decide_action(self, intent_data: dict) -> dict:
        system_prompt = """당신은 법률 팩트체커 시스템의 '두 번째 단계(Agent)'를 담당하는 판단 엔진입니다.
앞 단계(Input Hook)에서 분석된 사용자의 질문 의도와 키워드 정보를 바탕으로, 이 질문에 대답하기 위해 어떤 외부 도구/플러그인이 필요한지 결정해야 합니다.

**의사결정 규칙:**
1. **requires_law_db_search**: 법률(근로기준법 등) 질문이면 기본적으로 True로 설정합니다. 단, 질문이 법률과 전혀 무관하다면 False입니다.
2. **requires_precedent_search**: 사용자가 '부당해고', '직장내 괴롭힘' 등 법 조문만으로 흑백이 갈리지 않고 실제 법원이나 노동위원회의 과거 판정 사례를 참고해야 하는 경우 True로 설정합니다. 단순한 법령 문의(예: 최저임금이 얼마야?)는 False입니다.
3. **requires_calculator**: '얼마를 받을 수 있는지', '수당 계산', '퇴직금', '월급' 등 계산 로직이 들어가는 질문일 경우 True로 설정합니다.
4. **requires_clarification**: 사용자가 제공한 정보에 기간(언제부터 언제까지 일했는지), 규모(5인 미만 사업장 여부) 등 필수 법률 적용 요건이 심각하게 누락되어 팩트체크가 아예 불가능한 경우 True로 설정합니다.

반드시 아래의 지시사항에 따라 JSON 형태로만 응답하세요.

{format_instructions}
"""
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", "앞 단계 분석 결과: {intent_data}")
        ])

        chain = prompt | self.llm | self.parser
        
        try:
            result = await chain.ainvoke({
                "intent_data": str(intent_data),
                "format_instructions": self.parser.get_format_instructions()
            })
            return result
        except Exception as e:
            # Fallback in case of parsing error
            return {
                "requires_law_db_search": True,
                "requires_precedent_search": False,
                "requires_calculator": False,
                "requires_clarification": False,
                "reasoning": "분석 오류 발생. 기본적으로 법령 검색만 수행합니다."
            }
