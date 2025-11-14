import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import get_settings
from src.core.db import get_sessionmaker
from src.api.auth import router as auth_router

settings = get_settings()

openapi_tags = [
    {"name": "System", "description": "System and health endpoints"},
    {"name": "Authentication", "description": "User registration, login, and profile"},
]

# PUBLIC_INTERFACE
app = FastAPI(
    title="Reddit Curated Lists Backend",
    description="Backend APIs for authentication, Reddit OAuth linking, curated list management, scraping, and sharing.",
    version="0.1.0",
    openapi_tags=openapi_tags,
)

# Configure logging level from settings
logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
logger = logging.getLogger("reddit-backend")

# Do NOT force DB initialization here. App should boot without DB.
# Attempt a non-fatal lazy init on startup; never block or crash if DB is absent.
@app.on_event("startup")
async def startup_event():
    """
    Application startup hook.

    Behavior:
    - Attempts to initialize the DB sessionmaker lazily if a valid POSTGRES_URL is configured.
    - Never blocks or crashes the app if DB is absent or misconfigured.
    - Ensures the service responds on port 3001 (e.g., GET /) regardless of DB state.
    """
    try:
        # Accessing sessionmaker may raise if DB URL is missing/invalid; swallow and log.
        get_sessionmaker()
        logger.info("Database sessionmaker initialized successfully (if configured).")
    except Exception as e:
        logger.warning("Database is not ready or misconfigured at startup: %s", str(e))

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# PUBLIC_INTERFACE
@app.get("/", summary="Health Check", tags=["System"])
def health_check():
    """
    Health check to verify the API is responsive.

    Returns:
    - 200 with a simple JSON payload when the service is up, regardless of DB state.
    """
    return {"message": "Healthy"}


# Include routers (auth router uses an in-memory store; no DB access at import/startup)
app.include_router(auth_router)
