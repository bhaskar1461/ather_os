"""
Pydantic schemas for request/response validation across the API.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


# ── Auth Schemas ──────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=100)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


class VerifyEmailRequest(BaseModel):
    token: str


class OTPRequest(BaseModel):
    email: EmailStr


class OTPVerifyRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6)


class OTPResendRequest(BaseModel):
    email: EmailStr


class GoogleLoginRequest(BaseModel):
    credential: str | None = None
    access_token: str | None = None


# ── User Schemas ──────────────────────────────────────────────────────────────

class UserResponse(BaseModel):
    id: UUID
    email: str
    name: str | None = None
    avatar_url: str | None = None
    role: str
    is_verified: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    avatar_url: str | None = None


# ── Workspace Schemas ─────────────────────────────────────────────────────────

class WorkspaceCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None


class WorkspaceResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    owner_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Project Schemas ───────────────────────────────────────────────────────────

class ProjectCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None


class ProjectResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Chat Schemas ──────────────────────────────────────────────────────────────

class ChatCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    model_id: str = Field(min_length=1, max_length=100)
    folder_id: UUID | None = None
    agent_id: UUID | None = None


class ChatUpdateRequest(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    is_pinned: bool | None = None
    is_archived: bool | None = None
    folder_id: UUID | None = None


class ChatResponse(BaseModel):
    id: UUID
    project_id: UUID
    folder_id: UUID | None
    model_id: str
    agent_id: UUID | None
    title: str
    is_pinned: bool
    is_archived: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Message Schemas ───────────────────────────────────────────────────────────

class MessageCreateRequest(BaseModel):
    content: str = Field(min_length=1)
    role: str = "user"


class MessageResponse(BaseModel):
    id: UUID
    chat_id: UUID
    role: str
    content: str
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    latency_ms: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Folder Schemas ────────────────────────────────────────────────────────────

class FolderCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    color: str | None = None


class FolderUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    color: str | None = None
    is_pinned: bool | None = None


class FolderResponse(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    color: str | None
    is_pinned: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── File Schemas ──────────────────────────────────────────────────────────────

class FileResponse(BaseModel):
    id: UUID
    name: str
    size: int
    mime_type: str
    status: str
    progress: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Settings Schemas ──────────────────────────────────────────────────────────

class SettingsUpdateRequest(BaseModel):
    system_theme: str | None = None
    font_size: str | None = None
    notifications_enabled: bool | None = None
    keyboard_shortcuts_enabled: bool | None = None


class SettingsResponse(BaseModel):
    system_theme: str
    font_size: str
    notifications_enabled: bool
    keyboard_shortcuts_enabled: bool

    model_config = {"from_attributes": True}


# ── Generic Schemas ───────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
    redis: str


class MessageDetail(BaseModel):
    message: str


# ── Astrology Schemas ──────────────────────────────────────────────────────────

class AstrologyChartRequest(BaseModel):
    year: int = Field(..., ge=1900, le=2100)
    month: int = Field(..., ge=1, le=12)
    day: int = Field(..., ge=1, le=31)
    hour: int = Field(..., ge=0, le=23)
    minute: int = Field(..., ge=0, le=59)
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    timezone_offset: float = Field(..., ge=-12.0, le=14.0)


class AstrologyReadingRequest(AstrologyChartRequest):
    question: str | None = Field(None, max_length=1000)
    force_refresh: bool = Field(False, description="Bypass cache and force regenerate")


# ── Astrology V2 Schemas (Location-Resolved) ──────────────────────────────────

class AstrologyReadingRequestV2(BaseModel):
    """
    V2 astrology reading request using resolved location data.
    Users provide a city name — the frontend resolves coordinates
    and timezone via the /location/search endpoint before submission.
    """
    year: int = Field(..., ge=1900, le=2100)
    month: int = Field(..., ge=1, le=12)
    day: int = Field(..., ge=1, le=31)
    hour: int = Field(..., ge=0, le=23)
    minute: int = Field(..., ge=0, le=59)
    location_name: str = Field(..., min_length=1, max_length=200)
    location_lat: float = Field(..., ge=-90.0, le=90.0)
    location_lon: float = Field(..., ge=-180.0, le=180.0)
    location_timezone: str = Field(..., min_length=1, max_length=100, description="IANA timezone (e.g. Asia/Kolkata)")
    question: str | None = Field(None, max_length=1000)
    report_type: str | None = Field(
        None,
        max_length=50,
        description="Report category ID for specialized prompt templates: personality, career, love, marriage, health, life-guidance, remedies, annual-forecast"
    )
    force_refresh: bool = Field(False, description="Bypass cache and force regenerate")
    stream: bool = Field(True, description="Stream the response via SSE if True, else return full JSON")



class PartnerBirthDetails(BaseModel):
    year: int = Field(..., ge=1900, le=2100)
    month: int = Field(..., ge=1, le=12)
    day: int = Field(..., ge=1, le=31)
    hour: int = Field(..., ge=0, le=23)
    minute: int = Field(..., ge=0, le=59)
    location_name: str = Field(..., min_length=1, max_length=200)
    location_lat: float = Field(..., ge=-90.0, le=90.0)
    location_lon: float = Field(..., ge=-180.0, le=180.0)
    location_timezone: str = Field(..., min_length=1, max_length=100)

class CompatibilityRequest(BaseModel):
    partner_a: PartnerBirthDetails
    partner_b: PartnerBirthDetails
    partner_a_name: str = Field("Partner A", max_length=100)
    partner_b_name: str = Field("Partner B", max_length=100)
    force_refresh: bool = Field(False, description="Bypass cache and force regenerate")


class TransitRequest(BaseModel):
    birth_year: int = Field(..., ge=1900, le=2100)
    birth_month: int = Field(..., ge=1, le=12)
    birth_day: int = Field(..., ge=1, le=31)
    birth_hour: int = Field(..., ge=0, le=23)
    birth_minute: int = Field(..., ge=0, le=59)
    birth_lat: float = Field(..., ge=-90.0, le=90.0)
    birth_lon: float = Field(..., ge=-180.0, le=180.0)
    birth_timezone: str = Field(..., min_length=1, max_length=100)
    
    current_lat: float = Field(..., ge=-90.0, le=90.0)
    current_lon: float = Field(..., ge=-180.0, le=180.0)
    current_timezone: str = Field(..., min_length=1, max_length=100)
    force_refresh: bool = Field(False, description="Bypass cache and force regenerate")


# ── Location Schemas ──────────────────────────────────────────────────────────

class LocationSearchResult(BaseModel):
    city: str
    state: str
    country: str
    latitude: float
    longitude: float
    timezone: str
    display_name: str
    geo_id: str


# ── PDF Export Schemas ────────────────────────────────────────────────────────

class AstrologyPDFMetadata(BaseModel):
    name: str
    birth_date: str
    birth_time: str
    birth_location: str
    analysis_date: str


class AstrologyPDFExportRequest(BaseModel):
    metadata: AstrologyPDFMetadata
    content_markdown: str

