from langchain_core.messages import HumanMessage
import logging

from app.core.llm import get_main_llm

logger = logging.getLogger(__name__)

class VisionAnalyzer:
    """
    사용자가 업로드한 이미지를 분석하여 텍스트 및 법률적 맥락 정보를 추출하는 비전(Vision) 기반 분석 서비스.
    """
    def __init__(self):
        """
        VisionAnalyzer 생성자.
        이미지 문서 분석과 긴 분량의 텍스트 판독을 지원하기 위해 출력 토큰 한도(max_tokens=1000)가 늘어난 주(Main) LLM을 초기화합니다.
        """
        self.llm = get_main_llm(max_tokens=1000)

    async def extract_text_from_image(self, base64_image: str) -> str:
        """
        Base64 인코딩된 이미지 데이터를 받아서 머신비전 AI 모델로 판독하고,
        해당 문서의 종류와 법률적 팩트(임금, 기간, 독소조항 등)를 추출 및 요약하여 반환합니다.

        Args:
            base64_image (str): 사용자(클라이언트)가 첨부한 원본 이미지의 Base64 인코딩 문자열

        Returns:
            str: 비전 AI가 판독하여 법률적 관점으로 건조하게 요약해 낸 Markdown 결과 텍스트 반환
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
            logger.error(f"Vision Analysis Failed: {e}")
            return f"[이미지 분석 실패: {e}]\n사용자가 이미지를 첨부했으나, 서버 또는 모델 오류로 이미지를 읽을 수 없습니다."
