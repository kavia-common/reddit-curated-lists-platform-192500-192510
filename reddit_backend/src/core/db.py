from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from src.core.config import get_settings

_settings = get_settings()

# Create async engine using POSTGRES_URL. Expect async driver in URL (e.g., postgresql+asyncpg://)
DATABASE_URL = (_settings.POSTGRES_URL or "").strip()

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
    _validate_database_url(DATABASE_URL)
    return create_async_engine(DATABASE_URL, future=True, pool_pre_ping=True)


# Create a singleton engine and sessionmaker for app lifecycle
_engine: Optional[AsyncEngine] = None
_sessionmaker: Optional[async_sessionmaker[AsyncSession]] = None


def _ensure_engine():
    global _engine, _sessionmaker
    if _engine is None:
        _engine = get_engine()
        _sessionmaker = async_sessionmaker(bind=_engine, expire_on_commit=False)


# PUBLIC_INTERFACE
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """Return the AsyncSession sessionmaker, initializing if needed."""
    _ensure_engine()
    assert _sessionmaker is not None
    return _sessionmaker


# PUBLIC_INTERFACE
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an AsyncSession."""
    session_maker = get_sessionmaker()
    async with session_maker() as session:
        yield session
