"""
TrOCR Text Recognition Provider
Recognizes text in images using Transformer-based OCR
Best for: Handwritten text recognition (can be fine-tuned)
"""
import os
from typing import Dict, Any, Optional
from PIL import Image
import torch

from backend.ocr.base_provider import OCRProvider
from backend.config import settings
from backend.utils.best_trocr_models import get_best_trocr_model

try:
    from transformers import TrOCRProcessor, VisionEncoderDecoderModel
    TROCR_AVAILABLE = True
except ImportError:
    TROCR_AVAILABLE = False


class TrocrProvider(OCRProvider):
    """
    TrOCR (Transformer-based OCR) provider
    
    Recognizes text in entire images using transformer models.
    Can be fine-tuned on handwritten forms for better accuracy.
    """
    
    def __init__(self, 
                 trocr_model_path: Optional[str] = None,
                 trocr_base_model: Optional[str] = None,
                 device: Optional[str] = None):
        """
        Initialize TrOCR provider
        
        Args:
            trocr_model_path: Path to custom fine-tuned TrOCR model (optional)
            trocr_base_model: Base TrOCR model to use if no custom model
            device: Device to use ('cuda', 'cpu', or None for auto)
        """
        self.trocr_model_path = trocr_model_path or getattr(settings, 'TROCR_CUSTOM_MODEL_PATH', None)
        # Use best available TrOCR model from HuggingFace
        self.trocr_base_model = trocr_base_model or get_best_trocr_model("accuracy")
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        
        # Initialize models lazily
        self._trocr_processor = None
        self._trocr_model = None
    
    def _get_trocr_model(self):
        """Lazy load TrOCR model and processor"""
        if self._trocr_model is None or self._trocr_processor is None:
            if not TROCR_AVAILABLE:
                raise ImportError(
                    "TrOCR not available. Install with: pip install transformers torch"
                )
            
            # Load TrOCR model
            model_path = self.trocr_model_path if (
                self.trocr_model_path and os.path.exists(self.trocr_model_path)
            ) else self.trocr_base_model
            
            try:
                self._trocr_processor = TrOCRProcessor.from_pretrained(model_path)
                self._trocr_model = VisionEncoderDecoderModel.from_pretrained(model_path)
                self._trocr_model.to(self.device)
                self._trocr_model.eval()
            except Exception as e:
                raise RuntimeError(
                    f"Failed to load TrOCR model from {model_path}: {e}"
                )
        
        return self._trocr_processor, self._trocr_model
    
    async def extract_text(self, image: Image.Image, language: Optional[str] = None) -> Dict[str, Any]:
        """
        Recognize text in image using TrOCR
        
        Args:
            image: PIL Image object
            language: Optional language code (not used for TrOCR, kept for compatibility)
        
        Returns:
            Dictionary with:
                - raw_text: Recognized text
                - confidence: Recognition confidence (estimated)
                - structured_data: Additional metadata
                - provider: "trocr"
        """
        try:
            processor, trocr_model = self._get_trocr_model()
            
            # Preprocess image
            pixel_values = processor(image, return_tensors="pt").pixel_values
            pixel_values = pixel_values.to(self.device)
            
            # Generate text
            with torch.no_grad():
                generated_ids = trocr_model.generate(pixel_values)
                generated_text = processor.batch_decode(
                    generated_ids, skip_special_tokens=True
                )[0]
            
            # TrOCR doesn't provide confidence scores, use default
            confidence = 85.0  # Estimated confidence for handwritten text
            
            return {
                "raw_text": generated_text.strip(),
                "confidence": confidence,
                "structured_data": {
                    "word_count": len(generated_text.split()),
                    "model": self.trocr_base_model if not self.trocr_model_path else "custom"
                },
                "provider": "trocr"
            }
        
        except Exception as e:
            return {
                "raw_text": "",
                "confidence": 0.0,
                "structured_data": {},
                "provider": "trocr",
                "error": str(e)
            }
    
    def is_available(self) -> bool:
        """Check if TrOCR is available"""
        if not TROCR_AVAILABLE:
            return False
        
        try:
            self._get_trocr_model()
            return True
        except Exception:
            return False
    
    def get_provider_name(self) -> str:
        """Return provider name"""
        return "trocr"
