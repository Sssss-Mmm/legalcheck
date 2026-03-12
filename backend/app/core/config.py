"""
애플리케이션 설정 중앙 관리 모듈
모든 환경변수와 설정값을 한 곳에서 관리합니다.
"""
import os
from functools import lru_cache


class Settings:
    """환경변수 기반 설정 클래스"""

    # --- OpenAI / LLM ---
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    MAIN_LLM_MODEL: str = os.getenv("MAIN_LLM_MODEL", "gpt-4o")
    MINI_LLM_MODEL: str = os.getenv("MINI_LLM_MODEL", "gpt-4o-mini")

    # --- Database ---
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "sqlite:///./legalcheck.db"
    )

    # --- Auth ---
    ADMIN_API_KEY: str = os.getenv("ADMIN_API_KEY", "")

    # --- CORS ---
    CORS_ORIGINS: list[str] = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    ]

    # --- External APIs ---
    LAW_GO_KR_API_KEY: str = os.getenv("LAW_GO_KR_API_KEY", "")

    # --- Vector Store ---
    VECTOR_STORE_PATH: str = os.getenv("VECTOR_STORE_PATH", "chroma_db")


@lru_cache()
def get_settings() -> Settings:
    return Settings()
