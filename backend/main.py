from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from backend.config import settings, is_desktop_app, get_data_dir
from backend.database import engine, Base
from backend.api.routes import upload, forms, files, documents, students, students_export, batch_upload, annotation, training, auto_label
from backend.api.routes import auth_routes, users_routes
from backend.seed_admin import seed_admin_if_empty
import os

# Create database tables (optional - will fail if DB not available)
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"Warning: Could not connect to database: {e}")
    print("The server will start, but database operations may fail.")

# Ensure upload directory exists
print(f"DEBUG: Starting backend")
print(f"DEBUG: is_desktop_app() = {is_desktop_app()}")
print(f"DEBUG: get_data_dir() = {get_data_dir()}")
print(f"DEBUG: settings.DATABASE_URL = {settings.DATABASE_URL}")
print(f"DEBUG: settings.UPLOAD_DIR = {settings.UPLOAD_DIR}")

try:
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
except PermissionError as e:
    print(f"WARNING: Could not create upload directory {settings.UPLOAD_DIR}: {e}")
    print(f"DATA_DIR environment variable: {os.environ.get('DATA_DIR', 'NOT SET')}")
    # Try to use a fallback location
    import tempfile
    fallback_upload_dir = os.path.join(tempfile.gettempdir(), "ocr_form_extractor", "uploads")
    os.makedirs(fallback_upload_dir, exist_ok=True)
    settings.UPLOAD_DIR = fallback_upload_dir
    print(f"Using fallback upload directory: {fallback_upload_dir}")

app = FastAPI(
    title="Student Admission Form Digitization System",
    description="OCR-based system for digitizing handwritten admission forms",
    version="1.0.0"
)


@app.on_event("startup")
def on_startup():
    if not getattr(settings, "AUTH_DISABLED", False):
        seed_admin_if_empty()

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
    # Development or Desktop: Allow all localhost origins and file:// protocol
    # This allows any port on localhost (5173, 5174, 5175, etc.) and file:// for Electron
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"(http://(localhost|127\.0\.0\.1):\d+|file://.*)",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include routers
app.include_router(upload.router, prefix="/api", tags=["upload"])
# IMPORTANT: export router is now part of forms router
app.include_router(forms.router, prefix="/api/forms", tags=["forms"])
app.include_router(files.router, prefix="/api", tags=["files"])
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(students_export.router, prefix="/api/students", tags=["students-export"])
app.include_router(students.router, prefix="/api/students", tags=["students"])
app.include_router(batch_upload.router, prefix="/api", tags=["batch-upload"])
app.include_router(annotation.router, prefix="/api", tags=["annotation"])
app.include_router(training.router, prefix="/api", tags=["training"])
app.include_router(auto_label.router, prefix="/api", tags=["auto-label"])
app.include_router(auth_routes.router, prefix="/api")
app.include_router(users_routes.router, prefix="/api")

# Serve uploaded files
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Determine frontend path
def get_frontend_path():
    """Get the path to frontend static files"""
    base_dir = os.path.dirname(os.path.dirname(__file__))
    
    if is_desktop_app():
        # Desktop mode: check multiple possible locations
        import sys
        possible_paths = [
            os.path.join(os.path.dirname(sys.executable), '..', 'frontend'),  # Packaged app
            os.path.join(base_dir, 'frontend', 'dist'),  # Vite build
            os.path.join(base_dir, 'out'),  # Next.js build (legacy)
        ]
        for path in possible_paths:
            abs_path = os.path.abspath(path)
            if os.path.exists(abs_path) and os.path.exists(os.path.join(abs_path, 'index.html')):
                return abs_path
        # Return first path even if not found (for error message)
        return os.path.abspath(possible_paths[0])
    else:
        # Development: check Vite's dist folder first, then 'out'
        vite_path = os.path.join(base_dir, 'frontend', 'dist')
        if os.path.exists(vite_path):
            return vite_path
        return os.path.join(base_dir, 'out')

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
    
    # Mount static files (support both Next.js and Vite)
    next_dir = os.path.join(FRONTEND_PATH, '_next')
    if os.path.exists(next_dir):
        app.mount("/_next", StaticFiles(directory=next_dir), name="next_static")
        
    assets_dir = os.path.join(FRONTEND_PATH, 'assets')
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets_static")
    
    # Catch-all for SPA routes - must be LAST
    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        """Handle SPA routing - serve index.html for all routes"""
        # Check if it's an API route
        if full_path.startswith('api/'):
            return HTMLResponse("Not found", status_code=404)
        
        # Check if file exists
        # This handles assets like favicon.ico, logo.png, etc.
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
