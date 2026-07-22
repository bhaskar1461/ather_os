"""
FastAPI dependency that extracts and verifies the current user from the Authorization header.
"""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session as DBSession

from packages.database.connection import get_db
from packages.database.models import User
from app.security.tokens import TokenError, verify_access_token

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
    db: DBSession = Depends(get_db),
) -> User:
    """
    Dependency that validates the Bearer token and returns the authenticated User model.

    Raises:
        HTTPException 401: If the token is missing, expired, or invalid.
        HTTPException 404: If the user no longer exists.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = verify_access_token(credentials.credentials)
    except TokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_str = payload.get("sub")
    if user_id_str is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload is missing subject claim",
        )

    try:
        user_id = UUID(user_id_str)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token contains an invalid user identifier",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User account no longer exists",
        )

    return user


async def require_verified_user(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Dependency that ensures the current user has verified their email.

    Raises:
        HTTPException 403: If the user is not verified.
    """
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification is required to access this resource",
        )
    return user


async def require_admin_user(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Dependency that ensures the current user has admin role.

    Raises:
        HTTPException 403: If the user is not an admin.
    """
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator privileges are required",
        )
    return user
