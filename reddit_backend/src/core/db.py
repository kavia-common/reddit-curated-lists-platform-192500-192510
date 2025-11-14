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


def _normalize_to_async_url(url: str) -> str:
    """
    Normalize a Postgres URL to the asyncpg scheme if possible.

    Behavior:
    - If empty, return empty (caller decides whether to raise).
    - If already 'postgresql+asyncpg://', return as-is.
    - If starts with 'postgresql://', auto-upgrade to 'postgresql+asyncpg://'
      and log a helpful warning.
    - Otherwise, return as-is (may be invalid; caller may raise later).

    This avoids import/startup failures by allowing a non-async URL to be
    upgraded only when building the async engine.
    """
    if not url:
        return url
    if url.startswith("postgresql+asyncpg://"):
        return url
    if url.startswith("postgresql://"):
        upgraded = "postgresql+asyncpg://" + url[len("postgresql://") :]
        logger.warning(
            "POSTGRES_URL used 'postgresql://' scheme; auto-upgrading to 'postgresql+asyncpg://'. "
            "Please update your configuration to avoid this warning. Upgraded URL will be used for engine creation."
        )
        return upgraded
    return url


def _validate_database_url_or_raise(url: str) -> str:
    """
    Validate that the database URL is configured. If a non-async Postgres URL
    is provided, attempt to auto-upgrade to asyncpg.

    Returns the validated (and possibly upgraded) URL.
    """
    if not url:
        raise RuntimeError(
            "POSTGRES_URL environment variable is not set. "
            "Provide an async SQLAlchemy URL like: "
            "postgresql+asyncpg://user:password@host:port/dbname"
        )
    normalized = _normalize_to_async_url(url)
    if not normalized.startswith("postgresql+asyncpg://"):
        raise RuntimeError(
            f"Invalid POSTGRES_URL scheme: {url}. "
            "It must use the 'postgresql+asyncpg://' scheme for async operation."
        )
    return normalized


# PUBLIC_INTERFACE
def get_engine() -> AsyncEngine:
    """Create and return an Async SQLAlchemy engine bound to POSTGRES_URL.

    This function validates the URL and guarantees use of asyncpg. It performs
    no module-import-time side effects and will auto-upgrade 'postgresql://'
    to 'postgresql+asyncpg://' with a warning log.
    """
    url = _get_database_url()
    validated_url = _validate_database_url_or_raise(url)
    return create_async_engine(validated_url, future=True, pool_pre_ping=True)


# Create a singleton engine and sessionmaker for app lifecycle (fully lazy)
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
    if not url:
        # No DB configured: skip creation silently (valid mode).
        logger.debug("POSTGRES_URL is empty; skipping engine creation until DB is needed/configured.")
        return

    # Attempt normalization (auto-upgrade) and then create the engine.
    normalized = _normalize_to_async_url(url)
    if not normalized.startswith("postgresql+asyncpg://"):
        # Still invalid after normalization; do not raise here to avoid startup failure.
        logger.warning(
            "POSTGRES_URL appears invalid for async operation (value: '%s'). "
            "Set to 'postgresql+asyncpg://...' to enable DB access.", url or "EMPTY"
        )
        return

    _engine = create_async_engine(normalized, future=True, pool_pre_ping=True)
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
