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
        """
        Settings 인스턴스를 초기화하며, os.getenv를 통해 시스템 환경변수들을 즉시 로드합니다.
        LLM 키, 데이터베이스 URI, JWT 비밀키 등 핵심 애플리케이션 설정값을 클래스 속성으로 바인딩합니다.
        """
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
        self.JWT_SECRET: str = os.getenv("JWT_SECRET", "super-secret-key-change-in-production")
        self.JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")

        # --- CORS ---
        self.CORS_ORIGINS: list[str] = [
            origin.strip()
            for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
        ]

        # --- External APIs ---
        self.LAW_GO_KR_API_KEY: str = os.getenv("LAW_GO_KR_API_KEY", "")

        # --- Vector Store ---
        self.VECTOR_STORE_PATH: str = os.getenv("VECTOR_STORE_PATH", "chroma_db")

        # --- Ingestion ---
        self.PDF_MAX_TEXT_LENGTH: int = int(os.getenv("PDF_MAX_TEXT_LENGTH", "40000"))


@lru_cache()
def get_settings() -> Settings:
    """
    모든 모듈에서 공유할 Settings 싱글톤 객체를 반환합니다.
    lru_cache 데코레이터 덕분에 캐시가 활용되어, 여러 번 호출해도 환경변수를 매번 재조회하지 않고 동일한 인스턴스를 반환합니다.

    Returns:
        Settings: 애플리케이션의 전역 설정값을 담은 인스턴스
    """
    return Settings()
