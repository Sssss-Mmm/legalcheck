"""
인증/인가 의존성 모듈
- get_current_user_id: 일반 사용자 API용 (X-User-ID 헤더)
- verify_admin: 관리자 API용 (X-Admin-Key 헤더)

TODO: 프로덕션 환경에서는 JWT 토큰 기반 인증으로 교체 필요
"""
import logging

from fastapi import Header, HTTPException
from app.core.config import get_settings

logger = logging.getLogger(__name__)

ADMIN_API_KEY = get_settings().ADMIN_API_KEY


async def get_current_user_id(
    x_user_id: int = Header(..., alias="X-User-ID"),
) -> int:
    """
    X-User-ID 헤더에서 사용자 ID를 추출합니다.
    쿼리 파라미터 대신 헤더를 사용하여 URL에 user_id가 노출되지 않도록 합니다.
    """
    if x_user_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid user ID")
    return x_user_id


async def verify_admin(
    x_admin_key: str | None = Header(None, alias="X-Admin-Key"),
) -> bool:
    """
    관리자 API 키를 검증합니다.
    ADMIN_API_KEY 환경변수가 설정되지 않은 경우 경고 로그를 남기고 통과합니다 (개발 모드).
    """
    if not ADMIN_API_KEY:
        logger.warning(
            "ADMIN_API_KEY not set — admin endpoints are unprotected. "
            "Set ADMIN_API_KEY in .env for production!"
        )
        return True

    if not x_admin_key or x_admin_key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin API key")
    return True
