"""
User management API (admin only).
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from backend.database import get_db, User
from backend.auth import hash_password
from backend.api.dependencies import RequireAdmin, get_current_user
from backend.models.auth_models import CurrentUser, UserCreate, UserUpdate, UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=list[UserResponse])
async def list_users(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(RequireAdmin),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    """List users (admin only)."""
    rows = db.query(User).order_by(User.username).offset(skip).limit(limit).all()
    return [UserResponse(id=u.id, username=u.username, email=u.email, role=u.role, is_active=u.is_active) for u in rows]


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: UserCreate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(RequireAdmin),
):
    """Create user (admin only)."""
    from backend.api.dependencies import get_user_by_username

    if get_user_by_username(db, body.username):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")
    u = User(
        username=body.username,
        email=body.email,
        hashed_password=hash_password(body.password),
        role=body.role,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return UserResponse(id=u.id, username=u.username, email=u.email, role=u.role, is_active=u.is_active)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(RequireAdmin),
):
    """Get user by id (admin only)."""
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserResponse(id=u.id, username=u.username, email=u.email, role=u.role, is_active=u.is_active)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    body: UserUpdate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(RequireAdmin),
):
    """Update user (admin only)."""
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if body.email is not None:
        u.email = body.email
    if body.role is not None:
        u.role = body.role
    if body.is_active is not None:
        u.is_active = body.is_active
    if body.password is not None:
        u.hashed_password = hash_password(body.password)
    db.commit()
    db.refresh(u)
    return UserResponse(id=u.id, username=u.username, email=u.email, role=u.role, is_active=u.is_active)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(RequireAdmin),
):
    """Delete user (admin only). Cannot delete self."""
    if user_id == user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete yourself")
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    db.delete(u)
    db.commit()
