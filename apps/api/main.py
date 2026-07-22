"""
AI Platform API — Application Entrypoint

Production-ready FastAPI application with:
- Structured logging
- CORS configuration
- Request middleware (ID tracking, latency)
- Global error handlers
- Health check endpoint
- Database and Redis lifecycle management
"""

import sys
import os

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


from app.config import get_settings
from app.middleware import (
    configure_logging,
    register_error_handlers,
    RequestMiddleware,
)
from app.middleware.logging import get_logger
from app.redis_manager import check_redis_health, close_redis_pools
from app.schemas import HealthResponse
from packages.database.connection import Base, engine
from sqlalchemy import text as sa_text
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

settings = get_settings()
logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan handler.
    Runs startup and shutdown logic for database tables and Redis pools.
    """
    configure_logging()
    logger.info("startup", app_name=settings.app_name, environment=settings.environment)

    # Verify Redis connectivity on startup, activating fallback if unreachable
    await check_redis_health()


    # ── P0 Startup Guards ─────────────────────────────────────────────────
    is_production = settings.environment.lower() in ("production", "prod")

    # Guard 1: Reject insecure JWT secret in production
    insecure_jwt = settings.jwt_secret_key in (
        "change-this-in-production-to-a-secure-random-string",
        "",
    )
    if insecure_jwt:
        if is_production:
            raise RuntimeError(
                "FATAL: jwt_secret_key is set to the insecure default. "
                "Set JWT_SECRET_KEY to a cryptographically random value before deploying."
            )
        logger.warning("insecure_jwt_secret", hint="Using default JWT secret — acceptable only in development")

    # Guard 2: Reject SQLite fallback in production
    from packages.database.connection import is_sqlite
    if is_sqlite:
        if is_production:
            raise RuntimeError(
                "FATAL: Database fell back to SQLite. "
                "Set DATABASE_URL to a reachable PostgreSQL instance before deploying."
            )
        logger.warning("sqlite_fallback_active", hint="Running on SQLite — acceptable only in development")

    # Guard 3: Reject InMemoryRedis in production
    from app.redis_manager import USE_MOCK_REDIS
    if USE_MOCK_REDIS:
        if is_production:
            raise RuntimeError(
                "FATAL: Redis is unreachable and fell back to InMemoryRedis. "
                "Token blacklists will not work across processes. "
                "Set REDIS_URL to a reachable Redis instance before deploying."
            )
        logger.warning("inmemory_redis_active", hint="Running on InMemoryRedis — token blacklists are per-process only")

    # ── Database Init ─────────────────────────────────────────────────────
    # Create database tables (in production, use Alembic migrations)
    try:
        Base.metadata.create_all(bind=engine)
        with engine.begin() as conn:
            conn.execute(sa_text("ALTER TABLE users ADD COLUMN IF NOT EXISTS name VARCHAR(100);"))
            conn.execute(sa_text("ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url VARCHAR(512);"))
        logger.info("database_ready")
    except Exception as e:
        logger.warning("database_init_warning", error=str(e))

    # Clean up expired sessions on startup (P1 fix — prevents unbounded table growth)
    try:
        from packages.database.models import Session as UserSession
        from packages.database.connection import SessionLocal
        from datetime import datetime, timezone
        cleanup_db = SessionLocal()
        deleted = cleanup_db.query(UserSession).filter(
            UserSession.expires_at < datetime.now(timezone.utc)
        ).delete()
        cleanup_db.commit()
        cleanup_db.close()
        if deleted > 0:
            logger.info("expired_sessions_cleaned", count=deleted)
    except Exception as e:
        logger.warning("session_cleanup_failed", error=str(e))

    yield

    # Shutdown
    await close_redis_pools()
    logger.info("shutdown_complete")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# ── Middleware Registration ───────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex="https://.*\\.trycloudflare\\.com" if settings.environment == "development" else None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)

app.add_middleware(RequestMiddleware)

# ── Error Handlers ────────────────────────────────────────────────────────────

register_error_handlers(app)

# Rate limit exceeded handler (slowapi)
app.state.limiter = None  # slowapi state placeholder
try:
    from app.routers.auth import limiter as auth_limiter
    app.state.limiter = auth_limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
except ImportError:
    pass


# ── Health Check ──────────────────────────────────────────────────────────────

@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="Service health check",
)
async def health_check() -> HealthResponse:
    """
    Returns the status of the API, database, and Redis connections.
    """
    redis_healthy = await check_redis_health()

    # Quick database check via engine connectivity
    db_status = "healthy"
    try:
        with engine.connect() as conn:
            conn.execute(sa_text("SELECT 1"))
    except Exception:
        db_status = "unhealthy"

    return HealthResponse(
        status="operational",
        version=settings.app_version,
        database=db_status,
        redis="healthy" if redis_healthy else "unhealthy",
    )


# ── Router Registration ──────────────────────────────────────────────────────

from app.routers import auth, users, workspaces, chats, folders, files, astrology, location, profiles

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(workspaces.router)
app.include_router(chats.router)
app.include_router(folders.router)
app.include_router(files.router)
app.include_router(astrology.router)
app.include_router(location.router)
app.include_router(profiles.router)
