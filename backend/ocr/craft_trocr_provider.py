"""
CRAFT + TrOCR Combined Provider
Combines CRAFT text detection with TrOCR text recognition for handwritten forms
Best for: Handwritten student admission forms with trainable models
"""
import os
from typing import Dict, Any, Optional, List, Tuple
from PIL import Image
import numpy as np
import torch

from backend.ocr.base_provider import OCRProvider
from backend.config import settings

try:
    from craft_text_detector import (
        Craft,
        read_image,
        get_prediction,
        export_detected_regions,
        export_extra_info,
        empty_cuda_cache
    )
    CRAFT_AVAILABLE = True
except ImportError:
    CRAFT_AVAILABLE = False

try:
    from transformers import TrOCRProcessor, VisionEncoderDecoderModel
    TROCR_AVAILABLE = True
except ImportError:
    TROCR_AVAILABLE = False


class CraftTrocrProvider(OCRProvider):
    """
    Combined CRAFT text detection + TrOCR text recognition provider
    
    CRAFT (Character Region Awareness for Text Detection) detects text regions
    TrOCR (Transformer-based OCR) recognizes text in those regions
    
    This combination is excellent for handwritten forms and can be fine-tuned
    on your specific form dataset.
    """
    
    def __init__(self, 
                 craft_model_path: Optional[str] = None,
                 trocr_model_path: Optional[str] = None,
                 trocr_base_model: Optional[str] = None,
                 device: Optional[str] = None):
        """
        Initialize CRAFT+TrOCR provider
        
        Args:
            craft_model_path: Path to custom CRAFT model (optional)
            trocr_model_path: Path to custom fine-tuned TrOCR model (optional)
            trocr_base_model: Base TrOCR model to use if no custom model
            device: Device to use ('cuda', 'cpu', or None for auto)
        """
        self.craft_model_path = craft_model_path or getattr(settings, 'CRAFT_MODEL_PATH', None)
        self.trocr_model_path = trocr_model_path or getattr(settings, 'TROCR_CUSTOM_MODEL_PATH', None)
        self.trocr_base_model = trocr_base_model or "microsoft/trocr-base-handwritten"
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        
        # Initialize models lazily
        self._craft_model = None
        self._trocr_processor = None
        self._trocr_model = None
        
    def _get_craft_model(self):
        """Lazy load CRAFT model"""
        if self._craft_model is None:
            if not CRAFT_AVAILABLE:
                raise ImportError(
                    "CRAFT not available. Install with: pip install craft-text-detector"
                )
            
            # Load CRAFT model
            if self.craft_model_path and os.path.exists(self.craft_model_path):
                self._craft_model = Craft(
                    device=self.device,
                    cuda=self.device == "cuda"
                )
            else:
                # Use default CRAFT model
                self._craft_model = Craft(
                    device=self.device,
                    cuda=self.device == "cuda"
                )
        
        return self._craft_model
    
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
        Extract text using CRAFT detection + TrOCR recognition
        
        Args:
            image: PIL Image object
            language: Optional language code (not used for TrOCR, kept for compatibility)
        
        Returns:
            Dictionary with:
                - raw_text: Combined text from all detected regions
                - confidence: Average confidence score
                - structured_data: Detected regions with bounding boxes and text
                - provider: "craft-trocr"
        """
        try:
            # Step 1: Detect text regions using CRAFT
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
            
            if not boxes:
                return {
                    "raw_text": "",
                    "confidence": 0.0,
                    "structured_data": {
                        "regions": [],
                        "word_count": 0
                    },
                    "provider": "craft-trocr"
                }
            
            # Step 2: Recognize text in each region using TrOCR
            processor, trocr_model = self._get_trocr_model()
            
            recognized_texts = []
            regions = []
            total_confidence = 0.0
            
            for i, box in enumerate(boxes):
                try:
                    # Extract region from image
                    x_coords = [point[0] for point in box]
                    y_coords = [point[1] for point in box]
                    
                    x_min, x_max = int(min(x_coords)), int(max(x_coords))
                    y_min, y_max = int(min(y_coords)), int(max(y_coords))
                    
                    # Add padding
                    padding = 5
                    x_min = max(0, x_min - padding)
                    y_min = max(0, y_min - padding)
                    x_max = min(image.width, x_max + padding)
                    y_max = min(image.height, y_max + padding)
                    
                    # Crop region
                    region = image.crop((x_min, y_min, x_max, y_max))
                    
                    # Skip if region is too small
                    if region.width < 10 or region.height < 10:
                        continue
                    
                    # Recognize text with TrOCR
                    pixel_values = processor(region, return_tensors="pt").pixel_values
                    pixel_values = pixel_values.to(self.device)
                    
                    with torch.no_grad():
                        generated_ids = trocr_model.generate(pixel_values)
                        generated_text = processor.batch_decode(
                            generated_ids, skip_special_tokens=True
                        )[0]
                    
                    if generated_text.strip():
                        recognized_texts.append(generated_text.strip())
                        regions.append({
                            "text": generated_text.strip(),
                            "bbox": {
                                "x": x_min,
                                "y": y_min,
                                "width": x_max - x_min,
                                "height": y_max - y_min
                            },
                            "points": box.tolist() if hasattr(box, 'tolist') else box
                        })
                        # TrOCR doesn't provide confidence, use default
                        total_confidence += 0.85
                
                except Exception as e:
                    # Skip regions that fail
                    continue
            
            # Combine all recognized text
            raw_text = " ".join(recognized_texts)
            avg_confidence = total_confidence / len(regions) if regions else 0.0
            
            return {
                "raw_text": raw_text,
                "confidence": avg_confidence * 100,  # Convert to 0-100 scale
                "structured_data": {
                    "regions": regions,
                    "word_count": len(raw_text.split()),
                    "region_count": len(regions)
                },
                "provider": "craft-trocr"
            }
        
        except Exception as e:
            return {
                "raw_text": "",
                "confidence": 0.0,
                "structured_data": {},
                "provider": "craft-trocr",
                "error": str(e)
            }
    
    def is_available(self) -> bool:
        """Check if CRAFT and TrOCR are available"""
        if not CRAFT_AVAILABLE or not TROCR_AVAILABLE:
            return False
        
        try:
            # Try to initialize models
            self._get_craft_model()
            self._get_trocr_model()
            return True
        except Exception:
            return False
    
    def get_provider_name(self) -> str:
        """Return provider name"""
        return "craft-trocr"
