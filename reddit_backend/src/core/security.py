from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from jose import jwt
from passlib.context import CryptContext

from src.core.config import get_settings

settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# PUBLIC_INTERFACE
def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return pwd_context.hash(password)


# PUBLIC_INTERFACE
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


ALGORITHM = "HS256"


# PUBLIC_INTERFACE
def create_access_token(data: Dict[str, Any], expires_minutes: Optional[int] = None) -> str:
    """Create a signed JWT token with an expiration."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes if expires_minutes is not None else settings.JWT_EXPIRES_MIN
    )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=ALGORITHM)
    return encoded_jwt


# PUBLIC_INTERFACE
def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT token, raising JWTError on failure."""
    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
    return payload


# PUBLIC_INTERFACE
async def get_current_user() -> Dict[str, Any]:
    """
    Placeholder dependency to retrieve the current user from the Authorization header.

    Note:
    - This is a stub and should be replaced by a proper OAuth2PasswordBearer flow.
    - For now, it returns a minimal user object for wiring purposes.
    """
    # In a future task, we will:
    # 1) Extract token from Authorization header via OAuth2PasswordBearer
    # 2) Validate token with decode_access_token
    # 3) Fetch user from DB with subject (sub) claim
    # Returning a placeholder structure so routes can depend on it without breaking.
    return {"id": "placeholder", "username": "anonymous"}
