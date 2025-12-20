from pydantic import Field, model_validator
from pydantic_settings import BaseSettings
from typing import List, Union, Optional
import os

class Settings(BaseSettings):
    # Database
    # Default to SQLite for easy setup, can be overridden with PostgreSQL
    DATABASE_URL: str = "sqlite:///./admission_forms.db"
    
    # OCR Provider (tesseract, google, azure, abbyy, tesseract-google-combined, combined, craft-trocr)
    OCR_PROVIDER: str = "craft-trocr"  # Default to CRAFT+TR-OCR for handwritten forms
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
    OCR_BENCHMARK_PROVIDERS: Optional[List[str]] = Field(
        default_factory=list,
        description="Optional list of providers to benchmark; defaults to enabled providers."
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
    
    # Custom Trained Model Paths
    TROCR_CUSTOM_MODEL_PATH: Optional[str] = Field(
        default=None,
        description="Path to custom fine-tuned TrOCR model"
    )
    CRAFT_MODEL_PATH: Optional[str] = Field(
        default=None,
        description="Path to custom CRAFT model (optional)"
    )
    
    # Batch Processing
    BATCH_MAX_CONCURRENT: int = 5
    BATCH_QUEUE_BACKEND: str = "memory"  # memory, redis
    
    # OCR Caching
    OCR_CACHE_ENABLED: bool = True
    
    # File Upload
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
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
    
    @model_validator(mode="before")
    @classmethod
    def parse_benchmark_providers(cls, values: dict) -> dict:
        """Handle empty string for OCR_BENCHMARK_PROVIDERS"""
        if isinstance(values, dict) and 'OCR_BENCHMARK_PROVIDERS' in values:
            if values['OCR_BENCHMARK_PROVIDERS'] == '' or values['OCR_BENCHMARK_PROVIDERS'] is None:
                values['OCR_BENCHMARK_PROVIDERS'] = []
        return values

    @model_validator(mode="after")
    def ensure_provider_configuration(cls, values: "Settings") -> "Settings":
        enabled_map: set[str] = set()
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

        if values.OCR_BENCHMARK_PROVIDERS and len(values.OCR_BENCHMARK_PROVIDERS) > 0:
            invalid = [
                provider for provider in values.OCR_BENCHMARK_PROVIDERS
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

