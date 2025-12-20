"""
CRAFT Text Detection Provider
Detects text regions in images (detection only, no recognition)
Useful for getting bounding boxes of text regions
"""
import os
from typing import Dict, Any, Optional
from PIL import Image
import numpy as np
import torch

from backend.ocr.base_provider import OCRProvider

try:
    from craft_text_detector import (
        Craft,
        get_prediction,
    )
    CRAFT_AVAILABLE = True
except ImportError:
    CRAFT_AVAILABLE = False


class CraftProvider(OCRProvider):
    """
    CRAFT (Character Region Awareness for Text Detection) provider
    
    Detects text regions in images and returns bounding boxes.
    Does not perform text recognition - use with TrOCR provider for recognition.
    """
    
    def __init__(self, 
                 craft_model_path: Optional[str] = None,
                 device: Optional[str] = None):
        """
        Initialize CRAFT provider
        
        Args:
            craft_model_path: Path to custom CRAFT model (optional)
            device: Device to use ('cuda', 'cpu', or None for auto)
        """
        self.craft_model_path = craft_model_path
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self._craft_model = None
    
    def _get_craft_model(self):
        """Lazy load CRAFT model"""
        if self._craft_model is None:
            if not CRAFT_AVAILABLE:
                raise ImportError(
                    "CRAFT not available. Install with: pip install craft-text-detector"
                )
            
            # Load CRAFT model
            self._craft_model = Craft(
                device=self.device,
                cuda=self.device == "cuda"
            )
        
        return self._craft_model
    
    async def extract_text(self, image: Image.Image, language: Optional[str] = None) -> Dict[str, Any]:
        """
        Detect text regions using CRAFT (detection only)
        
        Args:
            image: PIL Image object
            language: Optional language code (not used, kept for compatibility)
        
        Returns:
            Dictionary with:
                - raw_text: Empty (detection only)
                - confidence: Detection confidence
                - structured_data: Detected regions with bounding boxes
                - provider: "craft"
        """
        try:
            craft_model = self._get_craft_model()
            
            # Convert PIL to numpy array
            image_array = np.array(image.convert('RGB'))
            
            # Run CRAFT detection
            prediction_result = get_prediction(
                image=image_array,
                craft_net=craft_model.craft_net,
                text_threshold=0.7,
                link_threshold=0.4,
                low_text=0.4,
                cuda=self.device == "cuda",
                long_size=1280
            )
            
            # Get bounding boxes
            boxes = prediction_result.get("boxes", [])
            
            regions = []
            for i, box in enumerate(boxes):
                x_coords = [point[0] for point in box]
                y_coords = [point[1] for point in box]
                
                x_min, x_max = int(min(x_coords)), int(max(x_coords))
                y_min, y_max = int(min(y_coords)), int(max(y_coords))
                
                regions.append({
                    "bbox": {
                        "x": x_min,
                        "y": y_min,
                        "width": x_max - x_min,
                        "height": y_max - y_min
                    },
                    "points": box.tolist() if hasattr(box, 'tolist') else box
                })
            
            return {
                "raw_text": "",  # Detection only, no text
                "confidence": 85.0,  # Detection confidence
                "structured_data": {
                    "regions": regions,
                    "region_count": len(regions),
                    "note": "Text detection only - no recognition performed"
                },
                "provider": "craft"
            }
        
        except Exception as e:
            return {
                "raw_text": "",
                "confidence": 0.0,
                "structured_data": {},
                "provider": "craft",
                "error": str(e)
            }
    
    def is_available(self) -> bool:
        """Check if CRAFT is available"""
        if not CRAFT_AVAILABLE:
            return False
        
        try:
            self._get_craft_model()
            return True
        except Exception:
            return False
    
    def get_provider_name(self) -> str:
        """Return provider name"""
        return "craft"
