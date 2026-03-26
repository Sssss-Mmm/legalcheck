"""
애플리케이션 설정 중앙 관리 모듈
모든 환경변수와 설정값을 한 곳에서 관리합니다.
"""
import os
from functools import lru_cache


class Settings:
    """환경변수 기반 설정 클래스

    모든 환경변수는 인스턴스 생성 시점(__init__)에 읽어옵니다.
    이를 통해 load_dotenv() 이후에 get_settings()를 호출하면
    정확한 값을 보장합니다.
    """

    def __init__(self):
        # --- OpenAI / LLM ---
        self.OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
        self.MAIN_LLM_MODEL: str = os.getenv("MAIN_LLM_MODEL", "gpt-4o")
        self.MINI_LLM_MODEL: str = os.getenv("MINI_LLM_MODEL", "gpt-4o-mini")

        # --- Database ---
        self.DATABASE_URL: str = os.getenv(
            "DATABASE_URL", "sqlite:///./legalcheck.db"
        )

        # --- Auth ---
        self.ADMIN_API_KEY: str = os.getenv("ADMIN_API_KEY", "")

        # --- CORS ---
        self.CORS_ORIGINS: list[str] = [
            origin.strip()
            for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
        ]

        # --- External APIs ---
        self.LAW_GO_KR_API_KEY: str = os.getenv("LAW_GO_KR_API_KEY", "")

        # --- Vector Store ---
        self.VECTOR_STORE_PATH: str = os.getenv("VECTOR_STORE_PATH", "chroma_db")


@lru_cache()
def get_settings() -> Settings:
    return Settings()
