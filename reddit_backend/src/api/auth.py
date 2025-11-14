from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field

from src.core.config import get_settings
from src.core.security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)

settings = get_settings()

# NOTE: This is an in-memory user store used as a temporary placeholder until DB models are wired.
# Keys are lowercase emails for uniqueness.
_FAKE_USERS: Dict[str, Dict[str, str]] = {}


class TokenResponse(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field("bearer", description="Token type, always 'bearer' here")


class RegisterRequest(BaseModel):
    email: EmailStr = Field(..., description="User email (will be used as username)")
    password: str = Field(..., min_length=6, description="User password (min 6 characters)")
    username: Optional[str] = Field(None, description="Optional display username")


class RegisterResponse(BaseModel):
    id: str = Field(..., description="User identifier")
    email: EmailStr = Field(..., description="User email")
    username: Optional[str] = Field(None, description="Display username")


class MeResponse(BaseModel):
    id: str = Field(..., description="User identifier (email for now)")
    email: EmailStr = Field(..., description="User email")
    username: Optional[str] = Field(None, description="Display username")


def _get_user_by_email(email: str) -> Optional[Dict[str, str]]:
    return _FAKE_USERS.get(email.lower())


def _create_user(email: str, password: str, username: Optional[str]) -> Dict[str, str]:
    if _get_user_by_email(email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    hashed = hash_password(password)
    user = {
        "id": email.lower(),
        "email": email.lower(),
        "username": username or email.split("@")[0],
        "password_hash": hashed,
    }
    _FAKE_USERS[email.lower()] = user
    return user


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create a new user with email and password. This temporary implementation stores users in-memory until DB is integrated.",
    responses={
        201: {"description": "User created"},
        400: {"description": "Email already registered"},
    },
)
def register(payload: RegisterRequest) -> RegisterResponse:
    """
    Register a new user with email and password.

    Returns the created user's basic profile information.
    """
    user = _create_user(payload.email, payload.password, payload.username)
    return RegisterResponse(id=user["id"], email=user["email"], username=user["username"])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login to obtain JWT",
    description="Authenticate with email and password and receive a JWT bearer token.",
    responses={
        200: {"description": "Successful authentication"},
        401: {"description": "Invalid credentials"},
    },
)
def login(form_data: OAuth2PasswordRequestForm = Depends()) -> TokenResponse:
    """
    Authenticate user using OAuth2 password flow.
    - username field should carry the email.
    - password is the user's password.

    Returns a bearer JWT token upon success.
    """
    email = form_data.username.lower()
    user = _get_user_by_email(email)
    if not user or not verify_password(form_data.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # Subject will be the user id (email for now)
    claims = {"sub": user["id"]}
    token = create_access_token(claims, expires_minutes=settings.JWT_EXPIRES_MIN)
    return TokenResponse(access_token=token, token_type="bearer")


@router.get(
    "/me",
    response_model=MeResponse,
    summary="Get current user profile",
    description="Return the currently authenticated user's profile. Uses a placeholder dependency until full token parsing is implemented.",
    responses={
        200: {"description": "Current user returned"},
        401: {"description": "Unauthorized"},
    },
)
async def me(current_user: Dict[str, str] = Depends(get_current_user)) -> MeResponse:
    """
    Retrieve the current user's profile.

    Note: This relies on a placeholder get_current_user dependency that will be upgraded
    in a later step to parse and validate the JWT from the Authorization header and fetch from DB.
    """
    # If the placeholder is still active, try to decode token when present in 'token' key (future-proofing)
    # For now, return the minimal info the dependency provides.
    # When DB is integrated, this should fetch the user record by subject (sub).
    user_id = current_user.get("id", "unknown")
    username = current_user.get("username")
    # Attempt to discover email if id looks like an email
    email = current_user.get("email") or user_id
    return MeResponse(id=user_id, email=email, username=username)
