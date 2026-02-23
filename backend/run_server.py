"""
Standalone server entry point for PyInstaller builds
This file is used when packaging the backend as an executable
"""
import uvicorn
from backend.main import app

if __name__ == "__main__":
    import sys
    import os
    
    # Get port from environment or default to 8000
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "127.0.0.1")
    
    # Run the server
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )
