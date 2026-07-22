import os
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# Environment variable configuration with fallbacks for development
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://postgres:postgres@localhost:5432/ai_platform"
)

# Detect if PostgreSQL database is unreachable, fall back to local SQLite file
is_sqlite = DATABASE_URL.startswith("sqlite")
if not is_sqlite:
    env = os.getenv("ENVIRONMENT", "development").lower()
    is_prod = env in ("production", "prod")
    is_azure = os.getenv("WEBSITE_SITE_NAME") is not None or os.getenv("WEBSITE_INSTANCE_ID") is not None
    
    # Only allow SQLite fallback in non-production/non-Azure environments
    if not (is_prod or is_azure):
        try:
            # Quick test connection check
            temp_engine = create_engine(DATABASE_URL, connect_args={"connect_timeout": 2})
            with temp_engine.connect() as conn:
                pass
            temp_engine.dispose()
        except Exception:
            import logging
            logging.getLogger("database").warning("PostgreSQL unreachable — falling back to local SQLite")
            ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            SQLITE_PATH = os.path.join(ROOT_DIR, "local.db").replace('\\', '/')
            DATABASE_URL = f"sqlite:///{SQLITE_PATH}"
            is_sqlite = True

from sqlalchemy.pool import StaticPool

if is_sqlite:
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
else:
    # Optimized pooling configuration for production readiness
    engine = create_engine(
        DATABASE_URL,
        pool_size=20,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=1800,
        pool_pre_ping=True
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a database session and ensures clean closure.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
