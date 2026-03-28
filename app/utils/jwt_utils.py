import jwt
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.settings.config import settings

JWT_TOKEN_AUDIENCE = "react-fastapi-admin"
JWT_TOKEN_ISSUER = "react-fastapi-admin"


def _build_common_claims(
    *,
    user_id: int,
    session_version: int,
    token_type: str,
    expire_at: datetime,
    token_jti: str | None = None,
) -> dict:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "user_id": user_id,
        "token_type": token_type,
        "session_version": session_version,
        "iat": now,
        "exp": expire_at,
        "jti": token_jti or uuid4().hex,
        "aud": JWT_TOKEN_AUDIENCE,
        "iss": JWT_TOKEN_ISSUER,
    }

    return payload


def create_access_token(*, user_id: int, username: str, is_superuser: bool, session_version: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = _build_common_claims(
        user_id=user_id,
        session_version=session_version,
        token_type="access",
        expire_at=expire,
    )
    payload["username"] = username
    payload["is_superuser"] = is_superuser
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(*, user_id: int, session_version: int, refresh_token_jti: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    payload = _build_common_claims(
        user_id=user_id,
        session_version=session_version,
        token_type="refresh",
        expire_at=expire,
        token_jti=refresh_token_jti,
    )
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str, *, expected_type: str) -> dict:
    options = {
        "verify_signature": True,
        "verify_exp": True,
        "verify_aud": True,
        "verify_iss": True,
    }
    payload = jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
        audience=JWT_TOKEN_AUDIENCE,
        issuer=JWT_TOKEN_ISSUER,
        options=options,
    )
    if payload.get("token_type") != expected_type:
        raise jwt.InvalidTokenError("invalid token type")
    return payload
