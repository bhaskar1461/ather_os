"""
User management router — profile updates, settings, and preferences.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DBSession

from packages.database.connection import get_db
from packages.database.models import User, Setting, Preference
from app.security.dependencies import get_current_user
from app.schemas import (
    UserResponse,
    UserUpdateRequest,
    SettingsUpdateRequest,
    SettingsResponse,
    MessageDetail,
)

router = APIRouter(prefix="/users", tags=["Users"])


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Update current user profile",
)
async def update_profile(
    body: UserUpdateRequest,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> UserResponse:
    """
    Update the authenticated user's profile fields.
    Only provided (non-None) fields are updated.
    """
    if body.name is not None:
        user.name = body.name  # type: ignore[assignment]
    if body.avatar_url is not None:
        user.avatar_url = body.avatar_url  # type: ignore[assignment]

    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


@router.get(
    "/me/settings",
    response_model=SettingsResponse,
    summary="Get current user settings",
)
async def get_settings_endpoint(
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> SettingsResponse:
    """
    Return the application settings for the current user.
    """
    user_settings = db.query(Setting).filter(Setting.user_id == user.id).first()
    if not user_settings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Settings not found. This should not happen — contact support.",
        )
    return SettingsResponse.model_validate(user_settings)


@router.patch(
    "/me/settings",
    response_model=SettingsResponse,
    summary="Update current user settings",
)
async def update_settings(
    body: SettingsUpdateRequest,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> SettingsResponse:
    """
    Partially update application settings for the current user.
    """
    user_settings = db.query(Setting).filter(Setting.user_id == user.id).first()
    if not user_settings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Settings not found",
        )

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user_settings, field, value)

    db.commit()
    db.refresh(user_settings)
    return SettingsResponse.model_validate(user_settings)


@router.delete(
    "/me",
    response_model=MessageDetail,
    summary="Delete current user account",
)
async def delete_account(
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> MessageDetail:
    """
    Permanently delete the authenticated user's account and all associated data.
    This action is irreversible.
    """
    db.delete(user)
    db.commit()
    return MessageDetail(message="Your account has been permanently deleted")
