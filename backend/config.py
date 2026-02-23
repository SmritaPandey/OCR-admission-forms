from pydantic import Field, model_validator
from pydantic_settings import BaseSettings
from typing import List, Union, Set, Optional
import os
import sys

# Detect if running as a packaged desktop app
def is_desktop_app():
    """
    Check if running as a packaged Electron app.
    Checks both PyInstaller frozen state and DESKTOP_APP environment variable.
    """
    # Check for explicit environment variable from Electron
    if os.environ.get('DESKTOP_APP') == '1':
        return True
    # Check for PyInstaller frozen state
    return getattr(sys, 'frozen', False)

def get_data_dir():
    """Get the data directory for the desktop app"""
    if is_desktop_app():
        # Check if DATA_DIR environment variable is set (from Electron)
        # This is the preferred way as Electron handles the AppData path
        data_dir_env = os.environ.get('DATA_DIR')
        if data_dir_env:
            # Create directory if it doesn't exist
            try:
                os.makedirs(data_dir_env, exist_ok=True)
            except Exception:
                pass  # Will fail later if we can't create it
            return os.path.abspath(data_dir_env)
        
        # Fallback for when frozen but no DATA_DIR set (shouldn't happen with correct Electron setup)
        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)
            # Try to write relative to executable (might fail in Program Files)
            # but better than CWD
            return os.path.abspath(os.path.join(base_path, 'data'))
            
    return os.getcwd()

# Set environment variables for desktop mode
if is_desktop_app():
    data_dir = get_data_dir()
    env_file = os.path.join(data_dir, '.env')
    if os.path.exists(env_file):
        # Load .env manually for desktop mode
        from dotenv import load_dotenv
        load_dotenv(env_file)
    
    # Set credentials path
    creds_path = os.path.join(data_dir, 'google-cloud-credentials.json')
    if os.path.exists(creds_path):
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = creds_path
        
    # Force set critical paths to ensure absolute paths in AppData are used
    # This overrides any local .env files that might be present
    os.environ['DATABASE_URL'] = f"sqlite:///{os.path.join(data_dir, 'admission_forms.db')}"
    os.environ['UPLOAD_DIR'] = os.path.join(data_dir, "uploads")
    # Desktop: disable auth so single-user runs without login
    os.environ.setdefault('AUTH_DISABLED', '1')

class Settings(BaseSettings):
    # Database
    # Default to SQLite for easy setup, can be overridden with PostgreSQL
    # In desktop mode, this is overridden by os.environ above
    DATABASE_URL: str = "sqlite:///./admission_forms.db"
    
    # OCR Provider (tesseract, google-vision, azure, abbyy, tesseract-google-combined, combined, craft-trocr)
    OCR_PROVIDER: str = "google-vision"  # Default to Google Vision (best trained and most accurate)
    OCR_ENABLE_TESSERACT: bool = Field(True, description="Enable local Tesseract OCR provider.")
    OCR_ENABLE_GOOGLE_VISION: bool = Field(True, description="Enable Google Cloud Vision OCR provider.")
    OCR_ENABLE_GOOGLE_DOCUMENT_AI: bool = Field(False, description="Enable Google Document AI OCR provider.")
    OCR_ENABLE_TESSERACT_GOOGLE_COMBINED: bool = Field(True, description="Enable combined Tesseract+Google Vision provider (requires both Tesseract and Google Vision enabled).")
    OCR_ENABLE_AZURE_VISION: bool = Field(False, description="Enable Azure Computer Vision OCR provider.")
    OCR_ENABLE_AZURE_FORM_RECOGNIZER: bool = Field(False, description="Enable Azure Form Recognizer provider.")
    OCR_ENABLE_AWS_TEXTRACT: bool = Field(False, description="Enable AWS Textract OCR provider.")
    OCR_ENABLE_ABBYY: bool = Field(False, description="Enable ABBYY FineReader OCR provider.")
    OCR_ENABLE_CRAFT_TROCR: bool = Field(True, description="Enable CRAFT+TR-OCR provider for handwritten text recognition.")
    OCR_ENABLE_CRAFT: bool = Field(True, description="Enable CRAFT-only provider for text detection.")
    OCR_ENABLE_TROCR: bool = Field(True, description="Enable TR-OCR-only provider for text recognition.")
    OCR_ENABLE_CLAUDE_VISION: bool = Field(False, description="Enable Claude Vision for AI-powered OCR.")
    OCR_ENABLE_GPT4_VISION: bool = Field(False, description="Enable GPT-4 Vision for AI-powered OCR.")
    OCR_ENABLE_OLLAMA: bool = Field(False, description="Enable Ollama local vision models.")
    OCR_BENCHMARK_PROVIDERS: Optional[str] = Field(
        default=None,
        description="Optional comma-separated list of providers to benchmark."
    )

    # OCR Preprocessing
    OCR_PREPROCESSING_ENABLED: bool = Field(
        True, description="Enable preprocessing pipeline before passing images to OCR providers."
    )
    OCR_PREPROCESSING_ENHANCE_CONTRAST: bool = Field(
        True, description="Apply contrast enhancement during preprocessing."
    )
    OCR_PREPROCESSING_CONTRAST_FACTOR: float = Field(
        1.8, description="Multiplier applied when enhancing contrast."
    )
    OCR_PREPROCESSING_DENOISE: bool = Field(
        True, description="Apply median filtering to reduce noise."
    )
    OCR_PREPROCESSING_DENOISE_SIZE: int = Field(
        3, description="Window size for the median filter (must be an odd integer >= 3)."
    )
    OCR_PREPROCESSING_SHARPEN: bool = Field(
        True, description="Apply sharpening filter after contrast adjustments."
    )
    OCR_PREPROCESSING_SHARPNESS_FACTOR: float = Field(
        1.6, description="Multiplier applied when sharpening the image."
    )
    OCR_PREPROCESSING_SCALE_FACTOR: float = Field(
        2.0, description="Scale factor applied to images below the max dimension."
    )
    OCR_PREPROCESSING_MAX_DIMENSION: int = Field(
        2400,
        description="Maximum long-edge dimension after scaling. Set to 0 to disable the cap.",
    )
    OCR_PREPROCESSING_BINARIZE: bool = Field(
        True, description="Convert grayscale image to black/white after adjustments."
    )
    OCR_PREPROCESSING_BINARIZE_THRESHOLD: int = Field(
        -1,
        description="Threshold for binarization. Use -1 to auto-calculate based on image histogram.",
    )
    
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
    # Custom model ID (optional) - Use a trained custom model instead of prebuilt
    # Get this from Document Intelligence Studio after training your custom model
    AZURE_FORM_RECOGNIZER_CUSTOM_MODEL_ID: str = ""
    
    # AWS Textract (Good for forms and handwriting)
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"
    
    # ABBYY FineReader
    ABBYY_APPLICATION_ID: str = ""
    ABBYY_PASSWORD: str = ""
    ABBYY_SERVER_URL: str = ""  # For FineReader Server
    
    # OpenAI GPT-4 Vision
    OPENAI_API_KEY: str = ""
    OPENAI_VISION_MODEL: str = "gpt-4-vision-preview"
    
    # Anthropic Claude Vision
    ANTHROPIC_API_KEY: str = ""
    CLAUDE_VISION_MODEL: str = "claude-3-5-sonnet-20241022"
    
    # Ollama (Local Vision Models)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_VISION_MODEL: str = "llama3.2-vision"
    
    # Batch Processing
    BATCH_MAX_CONCURRENT: int = 5  # For 50k+ scale: use 10–20 with multiple workers
    BATCH_QUEUE_BACKEND: str = "memory"  # memory, redis (redis recommended at 50k+ scale)
    
    # OCR Caching
    OCR_CACHE_ENABLED: bool = True
    
    # File Upload
    # In desktop mode, this is overridden by os.environ above
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB; for 4+20–30 page PDFs use 100MB+
    ALLOWED_EXTENSIONS: List[str] = ["jpg", "jpeg", "png", "pdf", "tiff", "bmp"]
    
    # CORS
    CORS_ORIGINS: Union[str, List[str]] = Field(
        default="http://localhost:3000,http://localhost:5173",
        description="Allowed CORS origins (comma-separated string or list)."
    )
    
    # Environment
    ENVIRONMENT: str = Field(
        default="development",
        description="Environment: development, staging, or production"
    )
    
    # Auth (multi-user, RBAC)
    AUTH_DISABLED: bool = Field(
        default=False,
        description="If True, skip auth (e.g. desktop single-user). When DESKTOP_APP=1, can default True."
    )
    JWT_SECRET: str = Field(default="change-me-in-production-use-long-random-secret", description="Secret for JWT signing")
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    JWT_EXPIRE_MINUTES: int = Field(default=60 * 24 * 7, description="JWT expiry in minutes (default 7 days)")
    
    # Legacy CORS (for backward compatibility)
    _CORS_ORIGINS_LEGACY: List[str] = [
        "http://localhost:3000", 
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175"
    ]
    
    class Config:
        env_file = ".env"
        case_sensitive = True

    @model_validator(mode="after")
    def ensure_provider_configuration(cls, values: "Settings") -> "Settings":
        enabled_map: Set[str] = set()
        if values.OCR_ENABLE_TESSERACT:
            enabled_map.add("tesseract")
        if values.OCR_ENABLE_GOOGLE_VISION:
            enabled_map.update({"google-vision", "google"})
        if (values.OCR_ENABLE_TESSERACT_GOOGLE_COMBINED and 
            values.OCR_ENABLE_TESSERACT and values.OCR_ENABLE_GOOGLE_VISION):
            enabled_map.update({"tesseract-google-combined", "combined"})
        if values.OCR_ENABLE_GOOGLE_DOCUMENT_AI:
            enabled_map.add("google-documentai")
        if values.OCR_ENABLE_AZURE_VISION:
            enabled_map.update({"azure-vision", "azure"})
        if values.OCR_ENABLE_AZURE_FORM_RECOGNIZER:
            enabled_map.add("azure-form-recognizer")
        if values.OCR_ENABLE_AWS_TEXTRACT:
            enabled_map.add("aws-textract")
        if values.OCR_ENABLE_ABBYY:
            enabled_map.add("abbyy")
        if values.OCR_ENABLE_CRAFT_TROCR:
            enabled_map.add("craft-trocr")
        if values.OCR_ENABLE_CRAFT:
            enabled_map.add("craft")
        if values.OCR_ENABLE_TROCR:
            enabled_map.add("trocr")
        if values.OCR_ENABLE_CLAUDE_VISION:
            enabled_map.add("claude-vision")
        if values.OCR_ENABLE_GPT4_VISION:
            enabled_map.add("gpt4-vision")
        if values.OCR_ENABLE_OLLAMA:
            enabled_map.add("ollama")

        if len(enabled_map) >= 2:
            enabled_map.update({"multi", "best"})

        if not enabled_map:
            raise ValueError("At least one OCR provider must be enabled in configuration.")

        default_provider = values.OCR_PROVIDER.lower()
        if default_provider not in enabled_map:
            readable = ", ".join(sorted(enabled_map))
            raise ValueError(
                f"Default OCR provider '{values.OCR_PROVIDER}' is not enabled. "
                f"Choose one of: {readable}"
            )

        if values.OCR_BENCHMARK_PROVIDERS:
            providers_list = [p.strip() for p in values.OCR_BENCHMARK_PROVIDERS.split(",") if p.strip()]
            invalid = [
                provider for provider in providers_list
                if provider.lower() not in enabled_map
            ]
            if invalid:
                readable = ", ".join(sorted(enabled_map))
                raise ValueError(
                    f"OCR_BENCHMARK_PROVIDERS contains disabled providers: {', '.join(invalid)}. "
                    f"Enabled providers: {readable}"
                )

        return values

settings = Settings()

