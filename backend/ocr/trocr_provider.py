"""
TR-OCR-only Provider for Handwritten Text Recognition

This provider uses only TR-OCR (Transformer-Based OCR) for text recognition.
It expects the image to already contain text regions (you can use CRAFT first
to detect regions, then crop and pass to TR-OCR).
"""
import os
import torch
import numpy as np
from PIL import Image, ImageEnhance
from typing import Dict, Any, Optional
from backend.ocr.base_provider import OCRProvider

# Lazy imports to handle optional dependencies
try:
    from transformers import TrOCRProcessor, VisionEncoderDecoderModel
    TROCR_AVAILABLE = True
except ImportError:
    TROCR_AVAILABLE = False


class TrocrProvider(OCRProvider):
    """
    OCR provider using only TR-OCR for handwritten text recognition.
    
    This provider recognizes text in images but does not detect text regions.
    Best used after CRAFT has detected and cropped text regions.
    """
    
    def __init__(self, custom_model_path: Optional[str] = None):
        self.name = "trocr"
        self.trocr_processor = None
        self.trocr_model = None
        self.device = self._get_device()
        self.model_loaded = False
        self.custom_model_path = custom_model_path or os.getenv("TROCR_CUSTOM_MODEL_PATH")
        
    def _get_device(self) -> str:
        """Determine if GPU is available"""
        if torch.cuda.is_available():
            return "cuda"
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            return "mps"  # Apple Silicon
        else:
            return "cpu"
    
    def _load_models(self):
        """Lazy load models on first use"""
        if self.model_loaded:
            return
        
        if not TROCR_AVAILABLE:
            raise ImportError(
                "TR-OCR is not installed. Install with: "
                "pip install transformers torch"
            )
        
        try:
            print(f"Loading TR-OCR model on {self.device}...")
            model_name = "microsoft/trocr-base-handwritten"
            
            # Check for custom trained model
            if self.custom_model_path and os.path.exists(self.custom_model_path):
                print(f"Using custom trained model: {self.custom_model_path}")
                model_name = self.custom_model_path
            
            self.trocr_processor = TrOCRProcessor.from_pretrained(model_name)
            self.trocr_model = VisionEncoderDecoderModel.from_pretrained(model_name)
            self.trocr_model.to(self.device)
            self.trocr_model.eval()
            
            self.model_loaded = True
            print("TR-OCR model loaded successfully!")
            
        except Exception as e:
            raise Exception(f"Failed to load TR-OCR model: {str(e)}")
    
    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """Preprocess image for better recognition"""
        # Convert to RGB if needed
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Enhance contrast
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.2)
        
        return image
    
    async def extract_text(self, image: Image.Image, language: Optional[str] = None) -> Dict[str, Any]:
        """
        Recognize text in image using TR-OCR.
        
        This assumes the image contains text regions already.
        For best results, use CRAFT first to detect and crop regions.
        """
        if not self.model_loaded:
            self._load_models()
        
        try:
            # Preprocess image
            processed_image = self._preprocess_image(image)
            
            # Process with TR-OCR
            pixel_values = self.trocr_processor(
                images=processed_image,
                return_tensors="pt"
            ).pixel_values
            
            # Move to device
            pixel_values = pixel_values.to(self.device)
            
            # Generate text
            generated_ids = self.trocr_model.generate(pixel_values)
            generated_text = self.trocr_processor.batch_decode(
                generated_ids,
                skip_special_tokens=True
            )[0]
            
            return {
                'raw_text': generated_text,
                'confidence': 0.85,  # TR-OCR confidence estimate
                'provider': 'trocr'
            }
            
        except Exception as e:
            return {
                'raw_text': '',
                'confidence': 0.0,
                'provider': 'trocr',
                'error': str(e)
            }
    
    def is_available(self) -> bool:
        """Check if TR-OCR is available"""
        try:
            if not TROCR_AVAILABLE:
                return False
            return True
        except Exception:
            return False
    
    def get_provider_name(self) -> str:
        return "trocr"
