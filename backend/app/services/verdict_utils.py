"""
Verdict 파싱 유틸리티 모듈
LLM 응답의 verdict 문자열을 VerdictEnum으로 변환합니다.
"""
import logging
from app.models.law import VerdictEnum

logger = logging.getLogger(__name__)

# 정확한 매칭 맵
_VERDICT_MAP = {
    "TRUE": VerdictEnum.TRUE,
    "FALSE": VerdictEnum.FALSE,
    "PARTIAL": VerdictEnum.PARTIAL,
    "사실": VerdictEnum.TRUE,
    "사실 아님": VerdictEnum.FALSE,
    "일부 사실": VerdictEnum.PARTIAL,
}


def parse_verdict(verdict_str: str) -> VerdictEnum:
    """
    LLM이 다양한 형태로 반환할 수 있는 판정 결과(verdict) 문자열을
    시스템 표준인 VerdictEnum 열거형 객체로 매핑 및 변환합니다.
    정확한 매칭 → 부분 매칭 → 기본값(PARTIAL) 순으로 안전하게 시도합니다.

    Args:
        verdict_str (str): LLM이 생성한 판정 결과 원시 문자열 (예: "TRUE", "사실", "일부 사실" 등)

    Returns:
        VerdictEnum: 매핑이 성공한 시스템 내부 Verdict 고유 열거형 상수
    """
    normalized = verdict_str.strip().upper()

    # 1. 정확한 매칭
    result = _VERDICT_MAP.get(normalized)
    if result is not None:
        return result

    # 원본 문자열로도 시도 (한글 키 매칭용)
    result = _VERDICT_MAP.get(verdict_str.strip())
    if result is not None:
        return result

    # 2. 부분 매칭 (길이가 긴 것부터 체크)
    if "일부 사실" in verdict_str or "PARTIAL" in normalized:
        return VerdictEnum.PARTIAL
    if "사실 아님" in verdict_str or "FALSE" in normalized:
        return VerdictEnum.FALSE
    if "사실" in verdict_str or "TRUE" in normalized:
        return VerdictEnum.TRUE

    # 3. 기본값
    logger.warning(f"Unknown verdict string: {verdict_str}")
    return VerdictEnum.PARTIAL
