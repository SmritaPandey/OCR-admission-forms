from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.config import settings
from backend.database import engine, Base
from backend.api.routes import upload, forms, export, files, documents, students, batch_upload, annotation, training, auto_label
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
# For development, allow all localhost origins using regex pattern
# This allows any port on localhost (5173, 5174, 5175, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
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
app.include_router(batch_upload.router, prefix="/api", tags=["batch-upload"])
app.include_router(annotation.router, prefix="/api", tags=["annotation"])
app.include_router(training.router, prefix="/api", tags=["training"])
app.include_router(auto_label.router, prefix="/api", tags=["auto-label"])

# Serve uploaded files
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

@app.get("/")
async def root():
    return {"message": "Student Admission Form Digitization System API"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

