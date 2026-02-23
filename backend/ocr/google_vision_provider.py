from google.cloud import vision
from typing import Dict, Any, Optional
from PIL import Image
import io
import os
from pathlib import Path
from backend.ocr.base_provider import OCRProvider
from backend.config import settings

class GoogleVisionProvider(OCRProvider):
    """Google Cloud Vision API provider - excellent handwriting recognition"""
    
    def __init__(self):
        self.name = "google-vision"
        self._client = None
    
    def _resolve_credentials_path(self) -> Optional[str]:
        """Resolve and set credentials path"""
        creds_path = settings.GOOGLE_APPLICATION_CREDENTIALS or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        if not creds_path:
            return None
            
        # If already absolute and exists, use it
        if os.path.isabs(creds_path) and os.path.exists(creds_path):
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = creds_path
            return creds_path
            
        # Try relative to project root
        project_root = Path(__file__).parent.parent.parent.resolve()
        full_path = project_root / creds_path
        if full_path.exists():
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(full_path)
            return str(full_path)
            
        # Try relative to current working directory
        cwd_path = Path.cwd() / creds_path
        if cwd_path.exists():
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(cwd_path)
            return str(cwd_path)
            
        return None
    
    def _get_client(self):
        """Initialize and return Google Vision client"""
        if self._client is None:
            # Resolve and set credentials path
            creds_path = self._resolve_credentials_path()
            
            if creds_path:
                self._client = vision.ImageAnnotatorClient()
            elif settings.GOOGLE_CLOUD_API_KEY:
                self._client = vision.ImageAnnotatorClient()
            elif settings.GOOGLE_CLOUD_PROJECT_ID:
                self._client = vision.ImageAnnotatorClient()
            else:
                raise Exception("Google Cloud Vision credentials not configured. Set GOOGLE_APPLICATION_CREDENTIALS path.")
        return self._client
    
    async def extract_text(self, image: Image.Image, language: Optional[str] = None) -> Dict[str, Any]:
        """Extract text using Google Cloud Vision API"""
        try:
            client = self._get_client()
            
            # Convert PIL Image to bytes
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            
            # Create image object for Vision API
            vision_image = vision.Image(content=img_byte_arr.getvalue())
            
            # Perform text detection
            response = client.text_detection(image=vision_image)
            texts = response.text_annotations
            
            if not texts:
                return {
                    "raw_text": "",
                    "confidence": 0.0,
                    "structured_data": None,
                    "provider": self.get_provider_name()
                }
            
            # First text annotation contains the entire detected text
            raw_text = texts[0].description if texts else ""
            
            # Calculate average confidence from all detected text blocks
            confidences = []
            if len(texts) > 1:
                for text in texts[1:]:  # Skip first (full text), get individual blocks
                    if hasattr(text, 'bounding_poly'):
                        # Confidence is not directly available, use a default
                        confidences.append(0.95)  # Google Vision is typically very accurate
            
            avg_confidence = sum(confidences) / len(confidences) * 100 if confidences else 95.0
            
            return {
                "raw_text": raw_text.strip(),
                "confidence": round(avg_confidence, 2),
                "structured_data": None,
                "provider": self.get_provider_name()
            }
        except Exception as e:
            raise Exception(f"Google Cloud Vision API error: {str(e)}")
    
    def is_available(self) -> bool:
        """Check if Google Cloud Vision is configured"""
        try:
            # Check credentials file path (most common setup)
            creds_path = self._resolve_credentials_path()
            if creds_path:
                return True
            # Fallback to API key or project ID
            return bool(settings.GOOGLE_CLOUD_API_KEY or settings.GOOGLE_CLOUD_PROJECT_ID)
        except Exception:
            return False
    
    def get_provider_name(self) -> str:
        return "google-vision"

