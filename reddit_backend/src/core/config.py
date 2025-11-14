import os
from typing import List

from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()


class Settings(BaseModel):
    """Application settings loaded from environment variables.

    Notes:
    - POSTGRES_URL must be an async SQLAlchemy URL using 'postgresql+asyncpg://'.
    - Leave POSTGRES_URL empty by default so the app can boot without DB; routes
      that require DB will raise clear errors when accessed.
    """
    # Database
    POSTGRES_URL: str = os.getenv("POSTGRES_URL", "")

    # Security / Auth
    JWT_SECRET: str = os.getenv("JWT_SECRET", "CHANGE_ME")
    JWT_EXPIRES_MIN: int = int(os.getenv("JWT_EXPIRES_MIN", "60"))

    # Reddit OAuth
    REDDIT_CLIENT_ID: str = os.getenv("REDDIT_CLIENT_ID", "")
    REDDIT_CLIENT_SECRET: str = os.getenv("REDDIT_CLIENT_SECRET", "")
    REDDIT_REDIRECT_URI: str = os.getenv("REDDIT_REDIRECT_URI", "")

    # App / CORS / Logging
    BASE_URL: str = os.getenv("BASE_URL", "http://localhost:3001")
    CORS_ALLOW_ORIGINS: List[str] = (
        [o.strip() for o in os.getenv("CORS_ALLOW_ORIGINS", "*").split(",")]
        if os.getenv("CORS_ALLOW_ORIGINS")
        else ["*"]
    )
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


# PUBLIC_INTERFACE
def get_settings() -> Settings:
    """Return cached Settings instance for application-wide use.

    Notes:
    - POSTGRES_URL may be empty to allow the app to boot without a database.
    - Database-dependent routes should handle missing DB gracefully.
    """
    # Simple module-level cache pattern
    global _settings
    try:
        return _settings
    except NameError:
        _settings = Settings()
        return _settings
