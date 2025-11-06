from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.config import settings
from backend.database import engine, Base
from backend.api.routes import upload, forms, export, files, documents, students
import os

# Create database tables (optional - will fail if DB not available)
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"Warning: Could not connect to database: {e}")
    print("The server will start, but database operations may fail.")

# Ensure upload directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

app = FastAPI(
    title="Student Admission Form Digitization System",
    description="OCR-based system for digitizing handwritten admission forms",
    version="1.0.0"
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(upload.router, prefix="/api", tags=["upload"])
app.include_router(forms.router, prefix="/api/forms", tags=["forms"])
app.include_router(export.router, prefix="/api/forms", tags=["export"])
app.include_router(files.router, prefix="/api", tags=["files"])
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(students.router, prefix="/api/students", tags=["students"])

# Serve uploaded files
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

@app.get("/")
async def root():
    return {"message": "Student Admission Form Digitization System API"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

