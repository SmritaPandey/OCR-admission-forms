from google.cloud import vision
from typing import Dict, Any, Optional
from PIL import Image
import io
from backend.ocr.base_provider import OCRProvider
from backend.config import settings

class GoogleVisionProvider(OCRProvider):
    """Google Cloud Vision API provider - excellent handwriting recognition"""
    
    def __init__(self):
        self.name = "google"
        self._client = None
    
    def _get_client(self):
        """Initialize and return Google Vision client"""
        if self._client is None:
            if settings.GOOGLE_CLOUD_API_KEY:
                self._client = vision.ImageAnnotatorClient()
            elif settings.GOOGLE_CLOUD_PROJECT_ID:
                self._client = vision.ImageAnnotatorClient()
            else:
                raise Exception("Google Cloud Vision API key or project ID not configured")
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
            return bool(settings.GOOGLE_CLOUD_API_KEY or settings.GOOGLE_CLOUD_PROJECT_ID)
        except Exception:
            return False
    
    def get_provider_name(self) -> str:
        return "google"

