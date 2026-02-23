"""
Shared dependencies for API routes.
"""
from typing import List

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import get_db, User
from backend.auth import decode_access_token
from backend.database import UserRole
from backend.models.auth_models import CurrentUser

# Default user when AUTH_DISABLED (e.g. desktop single-user)
_DEFAULT_USER = CurrentUser(id=0, username="default", role=UserRole.ADMIN.value)


def _bearer_token(request: Request) -> str | None:
    auth = request.headers.get("Authorization")
    if not auth or not auth.lower().startswith("bearer "):
        return None
    return auth[7:].strip()


async def get_current_user(request: Request) -> CurrentUser:
    """Resolve current user from JWT or default when auth disabled."""
    if settings.AUTH_DISABLED:
        return _DEFAULT_USER

    token = _bearer_token(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("user_id")
    username = payload.get("sub")
    role = payload.get("role", UserRole.VIEWER.value)
    if user_id is None or not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return CurrentUser(id=int(user_id), username=username, role=role)


def require_roles(allowed: List[str]):
    """Dependency that requires current user to have one of the given roles."""

    async def _check(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return _check


# Role aliases for route protection
RequireAdmin = require_roles([UserRole.ADMIN.value])
RequireStaffOrAdmin = require_roles([UserRole.ADMIN.value, UserRole.STAFF.value])
RequireAnyAuth = require_roles([UserRole.ADMIN.value, UserRole.STAFF.value, UserRole.VIEWER.value])


def get_user_by_username(db: Session, username: str) -> User | None:
    return db.query(User).filter(User.username == username).first()
