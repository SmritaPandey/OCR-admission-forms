"""
Seed initial admin user when no users exist.
Set SEED_ADMIN_PASSWORD in env; optionally SEED_ADMIN_USERNAME (default admin).
"""
import os
from backend.database import SessionLocal, User, UserRole
from backend.auth import hash_password


def seed_admin_if_empty():
    password = os.environ.get("SEED_ADMIN_PASSWORD")
    if not password:
        return
    username = os.environ.get("SEED_ADMIN_USERNAME", "admin")
    db = SessionLocal()
    try:
        if db.query(User).count() > 0:
            return
        u = User(
            username=username,
            hashed_password=hash_password(password),
            role=UserRole.ADMIN.value,
        )
        db.add(u)
        db.commit()
        print(f"Seeded admin user: {username}")
    except Exception as e:
        db.rollback()
        print(f"Seed admin failed: {e}")
    finally:
        db.close()
