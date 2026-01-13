from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from backend.config import settings, is_desktop_app, get_data_dir
from backend.database import engine, Base
from backend.api.routes import upload, forms, export, files, documents, students, students_export, batch_upload, annotation, training, auto_label
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
# Configure based on environment
if hasattr(settings, 'ENVIRONMENT') and settings.ENVIRONMENT == "production":
    # Production: Use configured CORS origins
    if isinstance(settings.CORS_ORIGINS, list):
        origins = settings.CORS_ORIGINS
    else:
        origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",")]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    # Development: Allow all localhost origins using regex pattern
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
app.include_router(students_export.router, prefix="/api/students", tags=["students-export"])
app.include_router(batch_upload.router, prefix="/api", tags=["batch-upload"])
app.include_router(annotation.router, prefix="/api", tags=["annotation"])
app.include_router(training.router, prefix="/api", tags=["training"])
app.include_router(auto_label.router, prefix="/api", tags=["auto-label"])

# Serve uploaded files
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Determine frontend path
def get_frontend_path():
    """Get path to static frontend files"""
    if is_desktop_app():
        # When running as packaged desktop app
        import sys
        base_path = os.path.dirname(sys.executable)
        frontend_path = os.path.join(base_path, '..', 'frontend')
        return os.path.abspath(frontend_path)
    else:
        # Development: frontend files in 'out' directory
        return os.path.join(os.path.dirname(os.path.dirname(__file__)), 'out')

FRONTEND_PATH = get_frontend_path()

# Serve static frontend files (for desktop app)
if os.path.exists(FRONTEND_PATH):
    print(f"Serving frontend from: {FRONTEND_PATH}")
    
    @app.get("/")
    async def serve_index():
        """Serve the main index.html"""
        index_path = os.path.join(FRONTEND_PATH, 'index.html')
        if os.path.exists(index_path):
            return FileResponse(index_path, media_type='text/html')
        return HTMLResponse("<h1>Frontend not found</h1>", status_code=404)
    
    # Mount static files (CSS, JS, images, etc.)
    app.mount("/_next", StaticFiles(directory=os.path.join(FRONTEND_PATH, '_next')), name="next_static")
    
    # Catch-all for SPA routes - must be LAST
    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        """Handle SPA routing - serve index.html for all routes"""
        # Check if it's an API route
        if full_path.startswith('api/'):
            return HTMLResponse("Not found", status_code=404)
        
        # Check if file exists
        file_path = os.path.join(FRONTEND_PATH, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        
        # For directory paths, look for index.html
        if full_path and not full_path.endswith('/'):
            dir_path = os.path.join(FRONTEND_PATH, full_path)
            if os.path.isdir(dir_path):
                index_path = os.path.join(dir_path, 'index.html')
                if os.path.exists(index_path):
                    return FileResponse(index_path, media_type='text/html')
        
        # Fallback to main index.html for SPA routing
        index_path = os.path.join(FRONTEND_PATH, 'index.html')
        if os.path.exists(index_path):
            return FileResponse(index_path, media_type='text/html')
        
        return HTMLResponse("<h1>Page not found</h1>", status_code=404)
else:
    print(f"Frontend path not found: {FRONTEND_PATH} - API only mode")
    
    @app.get("/")
    async def root():
        return {"message": "Student Admission Form Digitization System API"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
