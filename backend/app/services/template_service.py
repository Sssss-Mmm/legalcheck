from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

from app.core.llm import get_mini_llm

class TemplateOutput(BaseModel):
    document_title: str = Field(description="문서의 제목 (예: 임금체불 관련 진정서, 부당해고 구제신청서, 내용증명 등)")
    document_content: str = Field(description="마크다운 형식으로 작성된 문서 초안")

class DocumentTemplateGenerator:
    def __init__(self):
        self.llm = get_mini_llm(temperature=0.2)
        self.parser = JsonOutputParser(pydantic_object=TemplateOutput)
        
    async def generate_template(self, claim_text: str, explanation: str) -> dict:
        prompt = PromptTemplate(
            template="""당신은 대한민국 노동법 전문 노무사입니다. 사용자의 주장과 이에 대한 AI의 법률 팩트체크결과를 바탕으로, 
사용자가 취할 수 있는 현실적이고 가장 적절한 법적 조치(예: 고용노동부 진정서, 지방노동위원회 구제신청서, 사업주 대상 내용증명 우편 등) 하나를 선택하여 문서 초안을 작성해주세요.

작성 규칙 (필수):
1. 마크다운(Markdown) 포맷으로 깨끗하게 작성할 것 (표 제목 등 포함).
2. 사용자 이름란은 [진정인 이름], 사업주란은 [피진정인/회사 이름] 등의 자리표시자(Placeholder)로 비워둘 것. 날짜나 금액 등도 모른다면 [날짜], [금액] 등으로 표기할 것.
3. 문서의 제일 앞부분에 왜 이 양식을 추천하는지 1~2줄로 짧게 설명할 것.
4. 문서의 양식은 실제 제출할 수 있는 공식적인 구성(수신, 발신, 제목, 본문, 요건 사실, 날짜, 서명란 등)을 따를 것.
5. 문서의 마지막에 반드시 다음 면책 조항을 포함할 것:
   "**※ 주의사항**: 위 문서는 사용자의 주장을 바탕으로 AI가 자동 생성한 참고용 초안입니다. 법적 효력을 보장하지 않으며, 실제 공식 제출 전에 노무사나 변호사 등 전문가의 검토를 받으시기 바랍니다."

사용자 주장:
{claim_text}

팩트체크 요약 및 설명:
{explanation}

{format_instructions}""",
            input_variables=["claim_text", "explanation"],
            partial_variables={"format_instructions": self.parser.get_format_instructions()},
        )
        
        chain = prompt | self.llm | self.parser
        result = await chain.ainvoke({"claim_text": claim_text, "explanation": explanation})
        return result
