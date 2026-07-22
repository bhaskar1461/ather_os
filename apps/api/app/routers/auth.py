"""
Authentication router — login, register, refresh, logout, email verification, password reset.
"""

import secrets
import httpx
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session as DBSession

from packages.database.connection import get_db
from packages.database.models import User, Session as UserSession, Setting, Preference
from app.config import get_settings
from app.redis_manager import get_redis_tokens
from app.security.hashing import hash_password, verify_password
from app.security.tokens import (
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
    TokenError,
)
from app.security.dependencies import get_current_user
from app.services.email import (
    send_otp_email,
    send_verification_email,
    send_password_reset_email,
)
from app.schemas import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    RefreshRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    VerifyEmailRequest,
    OTPRequest,
    OTPVerifyRequest,
    OTPResendRequest,
    GoogleLoginRequest,
    UserResponse,
    MessageDetail,
)

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["Authentication"])
limiter = Limiter(key_func=get_remote_address)



@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
@limiter.limit("3/minute")
async def register(body: RegisterRequest, request: Request, db: DBSession = Depends(get_db)) -> UserResponse:
    """
    Create a new user account.
    Returns the created user. In production, an email verification link would be dispatched here.
    """
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists",
        )

    user = User(
        id=uuid4(),
        email=body.email,
        password_hash=hash_password(body.password),
        role="user",
        is_verified=True,
    )
    db.add(user)

    # Create default settings for the user
    user_settings = Setting(
        id=uuid4(),
        user_id=user.id,
        system_theme="dark",
        font_size="md",
        notifications_enabled=True,
        keyboard_shortcuts_enabled=True,
    )
    db.add(user_settings)

    # Create default preferences
    user_preferences = Preference(
        id=uuid4(),
        user_id=user.id,
    )
    db.add(user_preferences)

    db.commit()
    db.refresh(user)

    # Store a verification token in Redis (expires in 24h)
    verification_token = str(uuid4())
    redis = get_redis_tokens()
    await redis.setex(
        f"email_verify:{verification_token}",
        86400,  # 24 hours
        str(user.id),
    )

    # Dispatch email verification message via SMTP asynchronously
    await send_verification_email(user.email, verification_token)

    return UserResponse.model_validate(user)



@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate and receive JWT tokens",
)
@limiter.limit("5/minute")
async def login(
    body: LoginRequest,
    request: Request,
    db: DBSession = Depends(get_db),
) -> TokenResponse:
    """
    Authenticate with email and password.
    Returns access and refresh tokens on success.
    """
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    access_token = create_access_token(
        subject=str(user.id),
        extra_claims={"role": user.role, "email": user.email},
    )
    refresh_token = create_refresh_token(subject=str(user.id))

    # Persist session in the database
    session = UserSession(
        id=uuid4(),
        user_id=user.id,
        refresh_token=refresh_token,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(session)
    db.commit()

    # Cache the session in Redis for fast lookup during refresh
    redis = get_redis_tokens()
    await redis.setex(
        f"session:{refresh_token}",
        settings.refresh_token_expire_days * 86400,
        str(user.id),
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh an expired access token",
)
async def refresh_tokens(
    body: RefreshRequest,
    db: DBSession = Depends(get_db),
) -> TokenResponse:
    """
    Exchange a valid refresh token for a new access/refresh token pair.
    The old refresh token is revoked immediately.
    """
    try:
        payload = verify_refresh_token(body.refresh_token)
    except TokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    user_id = payload.get("sub")
    redis = get_redis_tokens()

    # Verify session exists in Redis
    cached = await redis.get(f"session:{body.refresh_token}")
    if not cached:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked",
        )

    from uuid import UUID as _UUID
    try:
        _uid = _UUID(user_id)
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token contains an invalid user identifier",
        )

    user = db.query(User).filter(User.id == _uid).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User account no longer exists",
        )

    # Revoke old session
    await redis.delete(f"session:{body.refresh_token}")
    db.query(UserSession).filter(
        UserSession.refresh_token == body.refresh_token
    ).delete()

    # Issue new tokens
    new_access = create_access_token(
        subject=str(user.id),
        extra_claims={"role": user.role, "email": user.email},
    )
    new_refresh = create_refresh_token(subject=str(user.id))

    session = UserSession(
        id=uuid4(),
        user_id=user.id,
        refresh_token=new_refresh,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(session)
    db.commit()

    await redis.setex(
        f"session:{new_refresh}",
        settings.refresh_token_expire_days * 86400,
        str(user.id),
    )

    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post(
    "/logout",
    response_model=MessageDetail,
    summary="Revoke the current session",
)
async def logout(
    body: RefreshRequest,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> MessageDetail:
    """
    Revoke the provided refresh token, ending the session.
    """
    redis = get_redis_tokens()
    await redis.delete(f"session:{body.refresh_token}")

    db.query(UserSession).filter(
        UserSession.refresh_token == body.refresh_token,
        UserSession.user_id == user.id,
    ).delete()
    db.commit()

    return MessageDetail(message="Session has been revoked successfully")


@router.post(
    "/verify-email",
    response_model=MessageDetail,
    summary="Verify email address with token",
)
async def verify_email(
    body: VerifyEmailRequest,
    db: DBSession = Depends(get_db),
) -> MessageDetail:
    """
    Verify a user's email address using the token sent during registration.
    """
    redis = get_redis_tokens()
    user_id = await redis.get(f"email_verify:{body.token}")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token",
        )

    from uuid import UUID as _UUID
    try:
        _uid = _UUID(str(user_id))
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification token data",
        )

    user = db.query(User).filter(User.id == _uid).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User account no longer exists",
        )

    user.is_verified = True
    db.commit()

    await redis.delete(f"email_verify:{body.token}")

    return MessageDetail(message="Email has been verified successfully")


# ── OTP Email Authentication ───────────────────────────────────────────────────

@router.post(
    "/otp/request",
    response_model=MessageDetail,
    summary="Request a 6-digit email OTP",
)
@limiter.limit("3/minute")
async def request_otp(
    body: OTPRequest,
    request: Request,
) -> MessageDetail:
    """
    Generate and send a 6-digit OTP code to the specified email address.
    Rate limited with a 60-second cooldown between resends.
    """
    redis = get_redis_tokens()
    
    # Check cooldown (60 seconds)
    cooldown = await redis.get(f"otp_cooldown:{body.email}")
    if cooldown:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Please wait 60 seconds before requesting another OTP.",
        )
    
    # Generate 6-digit OTP
    otp_code = "".join([str(secrets.randbelow(10)) for _ in range(6)])
    
    # Store OTP with 10-minute expiry (600s)
    await redis.setex(f"otp:{body.email}", 600, otp_code)
    # Store cooldown (60s)
    await redis.setex(f"otp_cooldown:{body.email}", 60, "1")
    # Reset retry attempt counter
    await redis.delete(f"otp_attempts:{body.email}")

    # Dispatch email via SMTP
    sent = await send_otp_email(body.email, otp_code)
    if not sent:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send OTP email. Please verify SMTP credentials.",
        )

    return MessageDetail(message=f"A 6-digit verification code has been sent to {body.email}")


@router.post(
    "/otp/verify",
    response_model=TokenResponse,
    summary="Verify OTP and authenticate user",
)
@limiter.limit("5/minute")
async def verify_otp(
    body: OTPVerifyRequest,
    request: Request,
    db: DBSession = Depends(get_db),
) -> TokenResponse:
    """
    Validate OTP code and issue access/refresh token pair.
    Automatically creates verified user account if it doesn't exist.
    """
    redis = get_redis_tokens()
    
    # Check retry attempts
    attempts_str = await redis.get(f"otp_attempts:{body.email}")
    attempts = int(attempts_str) if attempts_str else 0
    if attempts >= 5:
        await redis.delete(f"otp:{body.email}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Maximum OTP verification attempts exceeded. Please request a new OTP.",
        )

    stored_otp = await redis.get(f"otp:{body.email}")
    if not stored_otp or stored_otp != body.code:
        await redis.setex(f"otp_attempts:{body.email}", 600, str(attempts + 1))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP code",
        )

    # Clean up OTP state
    await redis.delete(f"otp:{body.email}")
    await redis.delete(f"otp_attempts:{body.email}")

    # Find or auto-create user
    user = db.query(User).filter(User.email == body.email).first()
    if not user:
        user = User(
            id=uuid4(),
            email=body.email,
            password_hash=hash_password(secrets.token_urlsafe(16)),
            role="user",
            is_verified=True,
        )
        db.add(user)
        db.add(Setting(id=uuid4(), user_id=user.id))
        db.add(Preference(id=uuid4(), user_id=user.id))
        db.commit()
        db.refresh(user)

    # Issue tokens & session
    access_token = create_access_token(
        subject=str(user.id),
        extra_claims={"role": user.role, "email": user.email},
    )
    refresh_token = create_refresh_token(subject=str(user.id))

    session = UserSession(
        id=uuid4(),
        user_id=user.id,
        refresh_token=refresh_token,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(session)
    db.commit()

    await redis.setex(
        f"session:{refresh_token}",
        settings.refresh_token_expire_days * 86400,
        str(user.id),
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post(
    "/otp/resend",
    response_model=MessageDetail,
    summary="Resend email OTP",
)
@limiter.limit("3/minute")
async def resend_otp(
    body: OTPResendRequest,
    request: Request,
) -> MessageDetail:
    """
    Resend OTP to the requested email.
    """
    return await request_otp(OTPRequest(email=body.email), request)


# ── Google OAuth Sign-In ───────────────────────────────────────────────────────

@router.post(
    "/google",
    response_model=TokenResponse,
    summary="Authenticate using Google OAuth 2.0 Token",
)
@limiter.limit("5/minute")
async def google_login(
    body: GoogleLoginRequest,
    request: Request,
    db: DBSession = Depends(get_db),
) -> TokenResponse:
    """
    Validate Google token, link or create user, and issue access/refresh token pair.
    """
    if not body.credential and not body.access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either Google ID token credential or access_token must be provided",
        )

    user_info = None
    async with httpx.AsyncClient(timeout=10.0) as client:
        if body.credential:
            resp = await client.get(
                "https://oauth2.googleapis.com/tokeninfo",
                params={"id_token": body.credential},
            )
            if resp.status_code == 200:
                user_info = resp.json()
        elif body.access_token:
            resp = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {body.access_token}"},
            )
            if resp.status_code == 200:
                user_info = resp.json()

    if not user_info or "email" not in user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Google authentication token",
        )

    email = user_info["email"]

    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            id=uuid4(),
            email=email,
            password_hash=hash_password(secrets.token_urlsafe(16)),
            role="user",
            is_verified=True,
        )
        db.add(user)
        db.add(Setting(id=uuid4(), user_id=user.id))
        db.add(Preference(id=uuid4(), user_id=user.id))
        db.commit()
        db.refresh(user)

    access_token = create_access_token(
        subject=str(user.id),
        extra_claims={"role": user.role, "email": user.email},
    )
    refresh_token = create_refresh_token(subject=str(user.id))

    session = UserSession(
        id=uuid4(),
        user_id=user.id,
        refresh_token=refresh_token,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(session)
    db.commit()

    redis = get_redis_tokens()
    await redis.setex(
        f"session:{refresh_token}",
        settings.refresh_token_expire_days * 86400,
        str(user.id),
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post(
    "/forgot-password",
    response_model=MessageDetail,
    summary="Request a password reset",
)
@limiter.limit("3/minute")
async def forgot_password(
    body: ForgotPasswordRequest,
    request: Request,
    db: DBSession = Depends(get_db),
) -> MessageDetail:
    """
    Initiate a password reset flow.
    Dispatches password reset email with reset token.
    The response is always the same to prevent email enumeration.
    """
    user = db.query(User).filter(User.email == body.email).first()

    if user:
        reset_token = str(uuid4())
        redis = get_redis_tokens()
        await redis.setex(
            f"pwd_reset:{reset_token}",
            3600,  # 1 hour expiry
            str(user.id),
        )
        await send_password_reset_email(user.email, reset_token)

    return MessageDetail(
        message="If an account with that email exists, a reset link has been sent"
    )



@router.post(
    "/reset-password",
    response_model=MessageDetail,
    summary="Reset password with token",
)
async def reset_password(
    body: ResetPasswordRequest,
    db: DBSession = Depends(get_db),
) -> MessageDetail:
    """
    Complete a password reset using the token from the forgot-password email.
    """
    redis = get_redis_tokens()
    user_id = await redis.get(f"pwd_reset:{body.token}")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    from uuid import UUID as _UUID
    try:
        _uid = _UUID(str(user_id))
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset token data",
        )

    user = db.query(User).filter(User.id == _uid).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User account no longer exists",
        )

    user.password_hash = hash_password(body.new_password)
    db.commit()

    await redis.delete(f"pwd_reset:{body.token}")

    # Revoke all existing sessions for security
    sessions = db.query(UserSession).filter(UserSession.user_id == user.id).all()
    for session in sessions:
        await redis.delete(f"session:{session.refresh_token}")
    db.query(UserSession).filter(UserSession.user_id == user.id).delete()
    db.commit()

    return MessageDetail(message="Password has been reset successfully. Please log in again.")


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get the authenticated user profile",
)
async def get_me(user: User = Depends(get_current_user)) -> UserResponse:
    """
    Return the profile of the currently authenticated user.
    """
    return UserResponse.model_validate(user)
