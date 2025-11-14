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
# Instead, attempt a non-fatal init on startup and log status.
@app.on_event("startup")
async def startup_event():
    """
    Try to initialize DB sessionmaker on startup, but do not crash the app if it fails.
    This keeps the app responsive (e.g., for health checks) even if DB is unavailable.
    """
    try:
        # This will raise only if someone attempts to use DB without configuration later.
        # Here, we call to try initialize; if not configured, it will raise and be caught.
        get_sessionmaker()
        logger.info("Database sessionmaker initialized successfully.")
    except Exception as e:
        logger.warning("Database is not ready or misconfigured at startup: %s", str(e))

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", summary="Health Check", tags=["System"])
def health_check():
    """Health check to verify the API is responsive."""
    return {"message": "Healthy"}


# Include routers
app.include_router(auth_router)
