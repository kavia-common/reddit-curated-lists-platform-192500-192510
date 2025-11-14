from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import get_settings
from src.core.db import get_sessionmaker  # ensure DB ready on import
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

# Initialize DB sessionmaker at startup time
get_sessionmaker()

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
