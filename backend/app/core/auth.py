"""
인증/인가 의존성 모듈
- get_current_user_id: 일반 사용자 API용 (JWT Bearer Token 검증)
- verify_admin: 관리자 API용 (X-Admin-Key 헤더)
- create_access_token: JWT 토큰 생성
"""
import logging
import jwt

from fastapi import Header, HTTPException
from app.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()
ADMIN_API_KEY = settings.ADMIN_API_KEY
JWT_SECRET = settings.JWT_SECRET
JWT_ALGORITHM = settings.JWT_ALGORITHM


def create_access_token(user_id: int) -> str:
    """JWT 토큰을 생성합니다."""
    payload = {"sub": str(user_id)}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


async def get_current_user_id(
    authorization: str = Header(..., description="Bearer JWT token"),
) -> int:
    """
    Authorization 헤더(Bearer 토큰)에서 JWT를 검증하고 user_id를 추출합니다.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header format")
    
    token = authorization.split("Bearer ")[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id_str = payload.get("sub")
        if user_id_str is None:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        return int(user_id_str)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


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
