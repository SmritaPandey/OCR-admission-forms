"""
Auth API: login, me, config.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from backend.database import get_db, User
from backend.auth import verify_password, create_access_token
from backend.api.dependencies import get_current_user, get_user_by_username
from backend.models.auth_models import Token, CurrentUser
from backend.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/config")
async def auth_config():
    """Public. Returns whether auth is enabled (frontend uses this to show login or skip)."""
    return {"auth_enabled": not settings.AUTH_DISABLED}


@router.post("/login", response_model=Token)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Login with username + password. Returns JWT."""
    if settings.AUTH_DISABLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Auth is disabled",
        )

    user = get_user_by_username(db, form.username)
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is inactive",
        )

    token = create_access_token(
        subject=user.username,
        role=user.role,
        user_id=user.id,
    )
    return Token(
        access_token=token,
        token_type="bearer",
        user_id=user.id,
        username=user.username,
        role=user.role,
    )


@router.get("/me", response_model=CurrentUser)
async def me(user: CurrentUser = Depends(get_current_user)):
    """Current user info (requires valid JWT). When auth disabled, returns default user."""
    return user
