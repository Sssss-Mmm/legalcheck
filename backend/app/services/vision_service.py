from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
import json

class VisionAnalyzer:
    def __init__(self):
        # We use gpt-4o as it has native vision capabilities and is usually the default anyway
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0, max_tokens=1000)

    async def extract_text_from_image(self, base64_image: str) -> str:
        """
        Base64 인코딩된 이미지를 받아서 GPT-4o 머신비전으로 텍스트를 읽고,
        그 문서가 무엇인지, 주요 팩트(임금, 기간, 독소조항 등)가 무엇인지 법률적 맥락에서 요약합니다.
        """
        
        # Make sure the base64 string doesn't have the data URL prefix if passed incorrectly
        if base64_image.startswith("data:image"):
            base64_image = base64_image.split(",")[1]
            
        system_instructions = """당신은 법률 팩트체커 시스템의 '문서/이미지 판독기(Vision AI)'입니다.
사용자가 첨부한 문서사진(근로계약서, 임금명세서, 진단서, 카카오톡 대화방 캡처 등)을 꼼꼼히 읽어주세요.

**역할 및 규칙:**
1. **문서 종류 파악**: 입력된 이미지가 어떤 종류의 문서인지 먼저 식별하세요 (예: 표준근로계약서, 급여명세서, 사직서, 메신저 대화 등).
2. **핵심 팩트 추출**: 법률 판단(팩트체크)에 기준이 될 만한 정보(날짜, 금액, 기간, 계약 당사자, 특약사항, 발언 내용 등)를 빠짐없이 추출하세요.
3. **위법/독소조항 감지(선택)**: 시급이 최저임금 미만이거나, 근로기준법에 위배되는 "휴게시간 무급 처리 동의" 같은 대표적인 독소/위법 조항이 보인다면 반드시 짚어주세요.
4. **객관적 요약**: 감정적인 해석을 배제하고 문서에 써진 '사실'만을 담담하고 건조하게 요약해서 Markdown 텍스트로 반환하세요.
"""

        message = HumanMessage(
            content=[
                {"type": "text", "text": system_instructions},
                {"type": "text", "text": "첨부된 이미지를 읽고 분석해주세요."},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}"
                    },
                },
            ]
        )

        try:
            response = await self.llm.ainvoke([message])
            return response.content.strip()
        except Exception as e:
            print(f"Vision Analysis Failed: {e}")
            return f"[이미지 분석 실패: {e}]\n사용자가 이미지를 첨부했으나, 서버 또는 모델 오류로 이미지를 읽을 수 없습니다."
