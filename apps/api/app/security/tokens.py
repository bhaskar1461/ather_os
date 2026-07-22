"""
JWT token utilities: creation, verification, and refresh logic.
"""

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from jose import JWTError, jwt

from app.config import get_settings

settings = get_settings()


class TokenError(Exception):
    """Raised when a token operation fails (expired, invalid, or revoked)."""
    pass


def create_access_token(subject: str, extra_claims: dict[str, Any] | None = None) -> str:
    """
    Create a short-lived JWT access token.

    Args:
        subject: The user ID or unique identifier to embed as the 'sub' claim.
        extra_claims: Optional dictionary of additional claims.

    Returns:
        Encoded JWT string.
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": subject,
        "exp": expire,
        "iat": now,
        "jti": str(uuid4()),
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(subject: str) -> str:
    """
    Create a long-lived JWT refresh token.

    Args:
        subject: The user ID or unique identifier.

    Returns:
        Encoded JWT string.
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=settings.refresh_token_expire_days)
    payload = {
        "sub": subject,
        "exp": expire,
        "iat": now,
        "jti": str(uuid4()),
        "type": "refresh",
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    """
    Decode and verify a JWT token.

    Args:
        token: The raw JWT string.

    Returns:
        Decoded payload dictionary.

    Raises:
        TokenError: If the token is expired, malformed, or signature is invalid.
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except JWTError as e:
        raise TokenError(f"Invalid token: {e}")


def verify_access_token(token: str) -> dict[str, Any]:
    """
    Decode an access token and assert it is of type 'access'.

    Returns:
        Decoded payload.

    Raises:
        TokenError: If not an access token or verification fails.
    """
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise TokenError("Token is not an access token")
    return payload


def verify_refresh_token(token: str) -> dict[str, Any]:
    """
    Decode a refresh token and assert it is of type 'refresh'.

    Returns:
        Decoded payload.

    Raises:
        TokenError: If not a refresh token or verification fails.
    """
    payload = decode_token(token)
    if payload.get("type") != "refresh":
        raise TokenError("Token is not a refresh token")
    return payload
