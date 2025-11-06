from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # Database
    # Default to SQLite for easy setup, can be overridden with PostgreSQL
    DATABASE_URL: str = "sqlite:///./admission_forms.db"
    
    # OCR Provider (tesseract, google, azure, abbyy)
    OCR_PROVIDER: str = "tesseract"
    
    # Google Cloud Vision
    GOOGLE_CLOUD_API_KEY: str = ""
    GOOGLE_CLOUD_PROJECT_ID: str = ""
    
    # Google Cloud Document AI (Best for forms and handwriting)
    GOOGLE_DOCUMENT_AI_PROJECT_ID: str = ""
    GOOGLE_DOCUMENT_AI_LOCATION: str = "us"  # us, eu, etc.
    GOOGLE_DOCUMENT_AI_PROCESSOR_ID: str = ""  # Form parser processor ID
    GOOGLE_APPLICATION_CREDENTIALS: str = ""  # Path to service account JSON
    
    # Azure Computer Vision
    AZURE_VISION_KEY: str = ""
    AZURE_VISION_ENDPOINT: str = ""
    
    # Azure Form Recognizer (Best for structured forms)
    AZURE_FORM_RECOGNIZER_KEY: str = ""
    AZURE_FORM_RECOGNIZER_ENDPOINT: str = ""
    
    # AWS Textract (Good for forms and handwriting)
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"
    
    # ABBYY FineReader
    ABBYY_APPLICATION_ID: str = ""
    ABBYY_PASSWORD: str = ""
    ABBYY_SERVER_URL: str = ""  # For FineReader Server
    
    # File Upload
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: List[str] = ["jpg", "jpeg", "png", "pdf", "tiff", "bmp"]
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()

