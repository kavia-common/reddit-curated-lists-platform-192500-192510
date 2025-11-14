from typing import AsyncGenerator, Optional
import logging

# Critically: never import create_engine (sync) to avoid psycopg2 paths.
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.config import get_settings

logger = logging.getLogger("reddit-backend.db")

# Settings are read lazily to avoid hard failures at import time.
_settings = get_settings()


def _get_database_url() -> str:
    """
    Return the configured database URL (may be empty).
    We avoid raising here to permit the app to boot without DB.
    """
    return (_settings.POSTGRES_URL or "").strip()


def _validate_database_url_or_raise(url: str) -> None:
    """
    Validate that the database URL is configured and uses the asyncpg driver.

    Enforce the 'postgresql+asyncpg://' scheme to ensure SQLAlchemy never tries
    to import psycopg2. This is called only at actual DB usage time.
    """
    if not url:
        raise RuntimeError(
            "POSTGRES_URL environment variable is not set. "
            "Provide an async SQLAlchemy URL like: "
            "postgresql+asyncpg://user:password@host:port/dbname"
        )
    if not url.startswith("postgresql+asyncpg://"):
        raise RuntimeError(
            f"Invalid POSTGRES_URL scheme: {url}. "
            "It must use the 'postgresql+asyncpg://' scheme for async operation."
        )


# PUBLIC_INTERFACE
def get_engine() -> AsyncEngine:
    """Create and return an Async SQLAlchemy engine bound to POSTGRES_URL.

    This function validates the URL and guarantees use of asyncpg. It performs
    no module-import-time side effects.
    """
    url = _get_database_url()
    _validate_database_url_or_raise(url)
    return create_async_engine(url, future=True, pool_pre_ping=True)


# Create a singleton engine and sessionmaker for app lifecycle (lazy)
_engine: Optional[AsyncEngine] = None
_sessionmaker: Optional[async_sessionmaker[AsyncSession]] = None


def _ensure_engine_initialized() -> None:
    """
    Initialize engine and sessionmaker on-demand.
    This function defers validation and potential failure until DB access.
    """
    global _engine, _sessionmaker
    if _engine is not None and _sessionmaker is not None:
        return

    url = _get_database_url()
    # If URL invalid or empty, do not raise here; let accessor raise with clear message.
    if not url or not url.startswith("postgresql+asyncpg://"):
        # Log only once at debug level to avoid noise; this is a valid "no-DB" boot mode.
        logger.debug("Database URL missing or invalid at lazy init; skipping engine creation.")
        return

    _engine = create_async_engine(url, future=True, pool_pre_ping=True)
    _sessionmaker = async_sessionmaker(bind=_engine, expire_on_commit=False)


# PUBLIC_INTERFACE
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """Return the AsyncSession sessionmaker, initializing if needed.

    Raises a clear error if database configuration is missing or invalid,
    ensuring callers only fail when they actually require DB access.
    """
    _ensure_engine_initialized()
    if _sessionmaker is None:
        url = _get_database_url()
        # Provide a clear, non-psycopg2 path message to keep users from configuring wrong driver.
        raise RuntimeError(
            "Database is not configured or URL scheme is invalid. "
            "Set POSTGRES_URL to an async URL using 'postgresql+asyncpg://'. "
            f"Current value: '{url or 'EMPTY'}'"
        )
    return _sessionmaker


# PUBLIC_INTERFACE
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an AsyncSession.

    The engine and sessionmaker are created lazily and validated to enforce
    asyncpg usage. This avoids any psycopg2 imports.
    """
    session_maker = get_sessionmaker()
    async with session_maker() as session:
        yield session
