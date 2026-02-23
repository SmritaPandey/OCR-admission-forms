"""
Authentication utilities: JWT and password hashing.
"""
from datetime import datetime, timedelta
from typing import Optional, Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from backend.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def create_access_token(
    subject: str,
    role: str,
    user_id: int,
    extra: Optional[dict] = None,
) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    to_encode: dict[str, Any] = {
        "sub": str(subject),
        "role": role,
        "user_id": user_id,
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    if extra:
        to_encode.update(extra)
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except JWTError:
        return None
