"""
Environment configuration for the FastAPI backend.
All settings are loaded from environment variables with sensible defaults.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application
    app_name: str = "AI Platform API"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "development"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/ai_platform"

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_token_db: int = 1

    # JWT
    jwt_secret_key: str = "change-this-in-production-to-a-secure-random-string"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # CORS
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ]

    # File Uploads
    max_upload_size_bytes: int = 10 * 1024 * 1024  # 10MB
    upload_directory: str = "./uploads"

    # Logging
    log_level: str = "INFO"

    # AWS / Bedrock
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_bearer_token_bedrock: str | None = None
    aws_region_name: str = "us-east-1"
    bedrock_model_id: str = "moonshotai.kimi-k2.5"

    # SMTP / Email Configuration
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = "bhaskarsharma0109@gmail.com"
    smtp_password: str = "cvey wkaa whdu lybj"
    smtp_from_email: str = "bhaskarsharma0109@gmail.com"
    smtp_from_name: str = "AetherOS"
    smtp_use_tls: bool = True

    # Google OAuth
    google_client_id: str | None = None

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


@lru_cache()
def get_settings() -> Settings:
    """
    Returns cached application settings.
    The lru_cache decorator ensures settings are only loaded once.
    """
    return Settings()
