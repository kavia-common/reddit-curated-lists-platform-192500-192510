import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import get_settings
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

# Do NOT perform any DB initialization on startup.
# Keep startup non-blocking and independent from DB configuration.
@app.on_event("startup")
async def startup_event():
    """
    Application startup hook.

    Behavior:
    - Does not initialize database connections.
    - Ensures the service responds on port 3001 regardless of DB state.
    - Logs that the app started successfully.
    """
    logger.info("FastAPI application startup: skipping DB initialization by design.")

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
