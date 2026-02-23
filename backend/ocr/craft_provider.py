"""
CRAFT-only Provider for Text Detection

This provider uses only CRAFT (Character Region Awareness for Text Detection) 
to detect text regions in images. It returns bounding boxes and detected regions
but does not perform text recognition.
"""
import os
import torch
import numpy as np
from PIL import Image
from typing import Dict, Any, Optional, List
from backend.ocr.base_provider import OCRProvider
import cv2
import tempfile

# Lazy imports to handle optional dependencies
try:
    from craft_text_detector import (
        Craft,
        read_image,
        get_prediction,
        export_detected_regions,
        export_extra_results,
        empty_cuda_cache
    )
    CRAFT_AVAILABLE = True
except ImportError:
    CRAFT_AVAILABLE = False
    try:
        from craft import Craft
        CRAFT_AVAILABLE = True
    except ImportError:
        CRAFT_AVAILABLE = False


class CraftProvider(OCRProvider):
    """
    OCR provider using only CRAFT for text region detection.
    
    This provider detects text regions but does not recognize the text.
    Useful for getting bounding boxes and text regions.
    """
    
    def __init__(self):
        self.name = "craft"
        self.craft_model = None
        self.device = self._get_device()
        self.model_loaded = False
        
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
        
        if not CRAFT_AVAILABLE:
            raise ImportError(
                "CRAFT is not installed. Install with: "
                "pip install craft-text-detector"
            )
        
        try:
            print(f"Loading CRAFT model on {self.device}...")
            temp_dir = tempfile.mkdtemp()
            
            self.craft_model = Craft(
                output_dir=temp_dir,
                crop_type="poly",
                cuda=self.device == "cuda",
                export_extra=True,
                text_threshold=0.7,
                link_threshold=0.4,
                low_text=0.4
            )
            
            self.model_loaded = True
            print("CRAFT model loaded successfully!")
            
        except Exception as e:
            raise Exception(f"Failed to load CRAFT model: {str(e)}")
    
    async def extract_text(self, image: Image.Image, language: Optional[str] = None) -> Dict[str, Any]:
        """
        Detect text regions using CRAFT.
        
        Returns bounding boxes and detected regions, but not recognized text.
        """
        if not self.model_loaded:
            self._load_models()
        
        # Convert PIL Image to numpy array for CRAFT
        img_array = np.array(image.convert('RGB'))
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        
        try:
            # Detect text regions
            if hasattr(self.craft_model, 'detect_text'):
                prediction_result = self.craft_model.detect_text(img_bgr)
            else:
                # Fallback to get_prediction
                prediction_result = get_prediction(
                    self.craft_model.craft_net,
                    self.craft_model.refine_net,
                    img_bgr,
                    text_threshold=0.7,
                    link_threshold=0.4,
                    low_text=0.4,
                    cuda=self.device == "cuda"
                )
            
            # Extract bounding boxes and regions
            boxes = []
            regions = []
            
            if isinstance(prediction_result, dict):
                boxes = prediction_result.get('boxes', [])
                regions = prediction_result.get('polys', [])
            elif isinstance(prediction_result, tuple):
                boxes = prediction_result[0] if len(prediction_result) > 0 else []
                regions = prediction_result[1] if len(prediction_result) > 1 else []
            
            # Combine detected regions into text (just coordinates for now)
            detected_text = f"Detected {len(boxes)} text regions"
            
            return {
                'raw_text': detected_text,
                'confidence': 0.8,  # Detection confidence
                'provider': 'craft',
                'boxes': boxes,
                'regions': regions,
                'region_count': len(boxes)
            }
            
        except Exception as e:
            return {
                'raw_text': '',
                'confidence': 0.0,
                'provider': 'craft',
                'error': str(e)
            }
    
    def is_available(self) -> bool:
        """Check if CRAFT is available"""
        try:
            if not CRAFT_AVAILABLE:
                return False
            return True
        except Exception:
            return False
    
    def get_provider_name(self) -> str:
        return "craft"
