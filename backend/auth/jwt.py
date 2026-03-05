"""
JWT 발급/검증 모듈

환경변수:
  JWT_SECRET_KEY: 필수. 미설정 시 모듈 임포트 시점에 ValueError 발생.
"""
import os
import logging
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

logger = logging.getLogger(__name__)

_ALGORITHM = "HS256"
_EXPIRE_DAYS = 7
_bearer_scheme = HTTPBearer()


def _get_secret() -> str:
    """JWT_SECRET_KEY 환경변수 반환. 미설정 시 즉시 실패."""
    secret = os.getenv("JWT_SECRET_KEY")
    if not secret:
        raise ValueError("JWT_SECRET_KEY 환경변수가 설정되지 않았습니다.")
    return secret


def create_access_token(user_id: int) -> str:
    """user_id를 sub 클레임으로 하는 JWT 생성. 만료: 7일."""
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(days=_EXPIRE_DAYS),
    }
    return jwt.encode(payload, _get_secret(), algorithm=_ALGORITHM)


def decode_access_token(token: str) -> int:
    """
    JWT 토큰을 검증하고 user_id(int)를 반환.
    유효하지 않으면 HTTP 401 발생.
    """
    try:
        payload = jwt.decode(token, _get_secret(), algorithms=[_ALGORITHM])
        user_id = int(payload["sub"])
        return user_id
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, KeyError, ValueError) as e:
        logger.warning("JWT 검증 실패: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않거나 만료된 토큰입니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> int:
    """
    FastAPI 의존성 — Authorization: Bearer 헤더에서 user_id 추출.
    토큰이 없거나 유효하지 않으면 401 반환.
    """
    return decode_access_token(credentials.credentials)
