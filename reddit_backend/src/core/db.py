from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from src.core.config import get_settings

_settings = get_settings()

# NOTE: Lazy-read URL to allow app boot without DB configured.
def _get_database_url() -> str:
    return (_settings.POSTGRES_URL or "").strip()


def _validate_database_url(url: str) -> None:
    """
    Validate that the database URL is configured and uses the asyncpg driver.

    We explicitly enforce the 'postgresql+asyncpg://' scheme to avoid SQLAlchemy
    attempting to import psycopg2 and failing with ModuleNotFoundError.
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
    """Create and return an Async SQLAlchemy engine bound to POSTGRES_URL."""
    url = _get_database_url()
    _validate_database_url(url)
    return create_async_engine(url, future=True, pool_pre_ping=True)


# Create a singleton engine and sessionmaker for app lifecycle
_engine: Optional[AsyncEngine] = None
_sessionmaker: Optional[async_sessionmaker[AsyncSession]] = None


def _ensure_engine() -> None:
    """
    Initialize engine and sessionmaker on-demand.
    This function defers failure until a DB access is attempted.
    """
    global _engine, _sessionmaker
    if _engine is None:
        url = _get_database_url()
        # Do not raise at import time if URL missing; postpone until first actual DB usage.
        if not url or not url.startswith("postgresql+asyncpg://"):
            # Leave engine/sessionmaker unset; will raise when accessed.
            return
        _engine = create_async_engine(url, future=True, pool_pre_ping=True)
        _sessionmaker = async_sessionmaker(bind=_engine, expire_on_commit=False)


# PUBLIC_INTERFACE
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """Return the AsyncSession sessionmaker, initializing if needed."""
    _ensure_engine()
    if _sessionmaker is None:
        # Provide a clear error only when callers actually need the DB.
        url = _get_database_url()
        raise RuntimeError(
            "Database is not configured or URL scheme is invalid. "
            "Set POSTGRES_URL to an async URL using 'postgresql+asyncpg://'. "
            f"Current value: '{url or 'EMPTY'}'"
        )
    return _sessionmaker


# PUBLIC_INTERFACE
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an AsyncSession."""
    session_maker = get_sessionmaker()
    async with session_maker() as session:
        yield session
