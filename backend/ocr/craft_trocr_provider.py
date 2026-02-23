"""
CRAFT + TR-OCR Provider for Handwritten Text Recognition

This provider combines:
- CRAFT (Character Region Awareness for Text Detection): Detects text regions in images
- TR-OCR (Transformer-Based OCR): Recognizes handwritten text using transformer models

Ideal for medical prescriptions, handwritten forms, and documents with handwritten text.
"""
import os
import torch
import numpy as np
from PIL import Image
from typing import Dict, Any, Optional, List, Tuple
from backend.ocr.base_provider import OCRProvider
import cv2
import requests
from io import BytesIO

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
    # Fallback: try alternative import
    try:
        from craft import Craft
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
    OCR provider using CRAFT for text detection and TR-OCR for handwritten text recognition.
    
    Workflow:
    1. CRAFT detects text regions (bounding boxes) in the image
    2. Each detected region is cropped and preprocessed
    3. TR-OCR recognizes the handwritten text in each region
    4. Results are combined into a single text output
    """
    
    def __init__(self, custom_model_path: Optional[str] = None):
        self.name = "craft-trocr"
        self.craft_model = None
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
        
        if not CRAFT_AVAILABLE:
            raise ImportError(
                "CRAFT is not installed. Install with: "
                "pip install craft-text-detector"
            )
        
        if not TROCR_AVAILABLE:
            raise ImportError(
                "TR-OCR is not installed. Install with: "
                "pip install transformers torch"
            )
        
        try:
            # Load CRAFT model for text detection
            print(f"Loading CRAFT model on {self.device}...")
            # Create temporary output directory for CRAFT
            import tempfile
            temp_dir = tempfile.mkdtemp()
            
            self.craft_model = Craft(
                output_dir=temp_dir,
                crop_type="poly",  # Polygon crop for better accuracy
                cuda=self.device == "cuda",
                export_extra=True,
                text_threshold=0.7,
                link_threshold=0.4,
                low_text=0.4
            )
            
            # Load TR-OCR model for handwritten text recognition
            # Check if custom trained model exists, otherwise use base model
            print(f"Loading TR-OCR model on {self.device}...")
            model_name = "microsoft/trocr-base-handwritten"
            
            # Check for custom trained model
            if self.custom_model_path and os.path.exists(self.custom_model_path):
                print(f"Using custom trained model: {self.custom_model_path}")
                model_name = self.custom_model_path
            
            self.trocr_processor = TrOCRProcessor.from_pretrained(model_name)
            self.trocr_model = VisionEncoderDecoderModel.from_pretrained(model_name)
            self.trocr_model.to(self.device)
            self.trocr_model.eval()  # Set to evaluation mode
            
            self.model_loaded = True
            print("CRAFT + TR-OCR models loaded successfully!")
            
        except Exception as e:
            raise Exception(f"Failed to load CRAFT+TR-OCR models: {str(e)}")
    
    def _detect_text_regions(self, image: Image.Image) -> List[Dict[str, Any]]:
        """
        Use CRAFT to detect text regions in the image.
        
        Returns:
            List of detected regions with bounding boxes and polygons
        """
        # Convert PIL Image to numpy array for CRAFT
        img_array = np.array(image.convert('RGB'))
        
        # CRAFT expects BGR format
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        
        # Get text detection predictions using CRAFT
        try:
            # Try using the craft_text_detector API
            if hasattr(self.craft_model, 'detect_text'):
                # Direct method if available
                prediction_result = self.craft_model.detect_text(img_bgr)
            else:
                # Use get_prediction function
                prediction_result = get_prediction(
                    image=img_bgr,
                    craft_net=self.craft_model.craft_net,
                    text_threshold=0.7,
                    link_threshold=0.4,
                    low_text=0.4,
                    cuda=self.device == "cuda",
                    long_size=1280
                )
        except Exception as e:
            # Fallback: use CRAFT's internal methods
            print(f"Warning: Using fallback CRAFT detection method: {e}")
            # Read image using CRAFT's read_image
            img = read_image(img_bgr)
            prediction_result = get_prediction(
                image=img,
                craft_net=self.craft_model.craft_net,
                text_threshold=0.7,
                link_threshold=0.4,
                low_text=0.4,
                cuda=self.device == "cuda",
                long_size=1280
            )
        
        # Extract bounding boxes and polygons
        regions = []
        
        # Handle different result formats
        if isinstance(prediction_result, dict):
            boxes = prediction_result.get('boxes', [])
        elif isinstance(prediction_result, tuple):
            # CRAFT sometimes returns (boxes, polys, heatmaps)
            boxes = prediction_result[0] if len(prediction_result) > 0 else []
        else:
            boxes = prediction_result if isinstance(prediction_result, (list, np.ndarray)) else []
        
        if len(boxes) > 0:
            # Convert to numpy array if needed
            if not isinstance(boxes, np.ndarray):
                boxes = np.array(boxes)
            
            for i, box in enumerate(boxes):
                # Handle different box formats
                if box.shape[0] < 4:  # Not enough points
                    continue
                
                # Convert box coordinates to integers
                box_int = box.astype(int) if isinstance(box, np.ndarray) else np.array(box, dtype=int)
                
                # Calculate bounding rectangle
                x_coords = box_int[:, 0] if len(box_int.shape) > 1 else [box_int[0]]
                y_coords = box_int[:, 1] if len(box_int.shape) > 1 else [box_int[1]]
                
                x_min, x_max = int(x_coords.min()), int(x_coords.max())
                y_min, y_max = int(y_coords.min()), int(y_coords.max())
                
                # Ensure coordinates are within image bounds
                x_min = max(0, x_min)
                y_min = max(0, y_min)
                x_max = min(image.width, x_max)
                y_max = min(image.height, y_max)
                
                if x_max > x_min and y_max > y_min:
                    regions.append({
                        'box': box_int,
                        'bbox': (x_min, y_min, x_max, y_max),
                        'polygon': box_int.tolist() if hasattr(box_int, 'tolist') else box_int
                    })
        
        return regions
    
    def _crop_region(self, image: Image.Image, bbox: Tuple[int, int, int, int]) -> Image.Image:
        """Crop a region from the image"""
        x_min, y_min, x_max, y_max = bbox
        return image.crop((x_min, y_min, x_max, y_max))
    
    def _preprocess_region(self, region_image: Image.Image) -> Image.Image:
        """
        Preprocess a cropped text region for better TR-OCR recognition.
        """
        # Convert to RGB if needed
        if region_image.mode != 'RGB':
            region_image = region_image.convert('RGB')
        
        # Resize if too small (TR-OCR works better with larger images)
        min_size = 32
        width, height = region_image.size
        if width < min_size or height < min_size:
            scale = max(min_size / width, min_size / height)
            new_size = (int(width * scale), int(height * scale))
            region_image = region_image.resize(new_size, Image.Resampling.LANCZOS)
        
        # Enhance contrast for better recognition
        from PIL import ImageEnhance
        enhancer = ImageEnhance.Contrast(region_image)
        region_image = enhancer.enhance(1.2)
        
        return region_image
    
    def _recognize_text(self, region_image: Image.Image) -> str:
        """
        Use TR-OCR to recognize handwritten text in a region.
        
        Args:
            region_image: PIL Image of the text region
            
        Returns:
            Recognized text string
        """
        try:
            # Preprocess the region
            processed_image = self._preprocess_region(region_image)
            
            # Process image with TR-OCR processor
            pixel_values = self.trocr_processor(
                images=processed_image,
                return_tensors="pt"
            ).pixel_values
            
            # Move to device
            pixel_values = pixel_values.to(self.device)
            
            # Generate text
            with torch.no_grad():  # Disable gradient computation for inference
                generated_ids = self.trocr_model.generate(pixel_values)
            
            # Decode the generated text
            generated_text = self.trocr_processor.batch_decode(
                generated_ids,
                skip_special_tokens=True
            )[0]
            
            return generated_text.strip()
            
        except Exception as e:
            # If recognition fails, return empty string
            print(f"TR-OCR recognition error: {str(e)}")
            return ""
    
    async def extract_text(
        self,
        image: Image.Image,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract handwritten text from image using CRAFT + TR-OCR.
        
        Args:
            image: PIL Image to process
            language: Optional language code (not used for TR-OCR, which is language-agnostic)
            
        Returns:
            Dictionary with extracted text and metadata
        """
        try:
            # Load models if not already loaded
            if not self.model_loaded:
                self._load_models()
            
            # Ensure image is RGB
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Step 1: Detect text regions using CRAFT
            print("Detecting text regions with CRAFT...")
            regions = self._detect_text_regions(image)
            
            if not regions:
                return {
                    "raw_text": "",
                    "confidence": 0.0,
                    "structured_data": None,
                    "provider": self.get_provider_name(),
                    "regions_detected": 0,
                    "regions": []
                }
            
            print(f"Found {len(regions)} text regions")
            
            # Step 2: Recognize text in each region using TR-OCR
            recognized_texts = []
            region_results = []
            
            for i, region in enumerate(regions):
                try:
                    # Crop the region
                    region_image = self._crop_region(image, region['bbox'])
                    
                    # Skip if region is too small
                    if region_image.size[0] < 10 or region_image.size[1] < 10:
                        continue
                    
                    # Recognize text
                    text = self._recognize_text(region_image)
                    
                    if text:
                        recognized_texts.append(text)
                        region_results.append({
                            'region_id': i + 1,
                            'text': text,
                            'bbox': region['bbox'],
                            'confidence': 0.85  # TR-OCR doesn't provide confidence, use default
                        })
                    
                    print(f"Region {i+1}/{len(regions)}: '{text[:50]}...'")
                    
                except Exception as e:
                    print(f"Error processing region {i+1}: {str(e)}")
                    continue
            
            # Step 3: Combine all recognized text
            combined_text = "\n".join(recognized_texts)
            
            # Calculate average confidence (placeholder, as TR-OCR doesn't provide per-token confidence)
            avg_confidence = 85.0 if recognized_texts else 0.0
            
            result = {
                "raw_text": combined_text,
                "confidence": round(avg_confidence, 2),
                "structured_data": None,
                "provider": self.get_provider_name(),
                "regions_detected": len(regions),
                "regions_recognized": len(region_results),
                "regions": region_results,
                "device": self.device
            }
            
            return result
            
        except Exception as e:
            error_msg = str(e)
            if "not installed" in error_msg.lower():
                raise Exception(
                    f"CRAFT+TR-OCR error: {error_msg}\n"
                    "Please install required dependencies:\n"
                    "pip install craft-text-detector transformers torch torchvision"
                )
            raise Exception(f"CRAFT+TR-OCR error: {error_msg}")
    
    def is_available(self) -> bool:
        """Check if CRAFT and TR-OCR are available"""
        try:
            # Check if dependencies are installed
            if not CRAFT_AVAILABLE or not TROCR_AVAILABLE:
                return False
            
            # Don't load models in is_available() - that's too slow
            # Just check if dependencies are available
            # Models will be loaded lazily on first use
            return True
            
        except Exception:
            return False
    
    def get_provider_name(self) -> str:
        return "craft-trocr"

