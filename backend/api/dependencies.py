from fastapi import Depends
from sqlalchemy.orm import Session
from backend.database import get_db

# Shared dependencies for API routes
__all__ = ["get_db"]

