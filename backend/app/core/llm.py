"""
LLM 인스턴스 중앙 관리 모듈
모델명 변경 시 이 파일만 수정하면 됩니다.
"""
from langchain_openai import ChatOpenAI
from app.core.config import get_settings


def get_main_llm(temperature: float = 0, **kwargs) -> ChatOpenAI:
    """메인 LLM (gpt-4o 기본) — 팩트체크, 의도 분석, 에이전트 등"""
    settings = get_settings()
    return ChatOpenAI(model=settings.MAIN_LLM_MODEL, temperature=temperature, **kwargs)


def get_mini_llm(temperature: float = 0, **kwargs) -> ChatOpenAI:
    """경량 LLM (gpt-4o-mini 기본) — 요약, 검증, 문서 생성 등"""
    settings = get_settings()
    return ChatOpenAI(model=settings.MINI_LLM_MODEL, temperature=temperature, **kwargs)
