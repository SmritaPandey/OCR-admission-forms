import pytesseract
from PIL import Image
from typing import Dict, Any, Optional
from backend.ocr.base_provider import OCRProvider
from backend.utils.image_preprocessing import enhance_for_ocr
import os
import platform

class TesseractProvider(OCRProvider):
    """Tesseract OCR provider - free, local OCR with enhanced settings"""
    
    def __init__(self):
        self.name = "tesseract"
        # Configure Tesseract path for Windows if not in PATH
        if platform.system() == "Windows":
            # First check if TESSERACT_CMD environment variable is set
            tesseract_cmd = os.environ.get('TESSERACT_CMD')
            if tesseract_cmd and os.path.exists(tesseract_cmd):
                pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
            else:
                # Try default installation paths
                default_paths = [
                    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                ]
                for path in default_paths:
                    if os.path.exists(path):
                        pytesseract.pytesseract.tesseract_cmd = path
                        break
    
    async def extract_text(self, image: Image.Image, language: Optional[str] = None, 
                          psm: Optional[int] = None, oem: Optional[int] = None,
                          preprocess: bool = True) -> Dict[str, Any]:
        """
        Extract text using Tesseract OCR with enhanced settings
        
        Args:
            image: PIL Image
            language: Language code (e.g., 'eng', 'eng+fra')
            psm: Page Segmentation Mode (0-13)
                6 = Assume uniform block of text
                11 = Sparse text
                12 = Sparse text with OSD
            oem: OCR Engine Mode (0-3)
                3 = Default, based on what is available
            preprocess: Apply image preprocessing for better accuracy
        """
        try:
            # Validate image
            if image is None:
                raise ValueError("Image object is None")
            
            # Ensure image is in RGB mode for Tesseract
            if image.mode not in ('RGB', 'L', '1'):
                image = image.convert('RGB')
            
            # Verify image is valid by checking size
            if image.size[0] == 0 or image.size[1] == 0:
                raise ValueError("Image has invalid dimensions")
            
            # Default to English if no language specified
            lang = language or "eng"
            
            # Preprocess image for better OCR results
            if preprocess:
                image = enhance_for_ocr(image)
            
            # Configure Tesseract options for best results
            config = ""
            
            # Page Segmentation Mode (PSM)
            # PSM 6 = Assume uniform block of text (good for forms)
            # PSM 11 = Sparse text (good for handwriting)
            # PSM 4 = Assume single column of text
            # PSM 12 = Sparse text with OSD
            if psm is None:
                # Auto-detect: try different PSMs and pick best
                # Try form-optimized modes first
                psm_options = [6, 4, 11, 12, 3]  # Uniform block, single column, sparse, sparse+OSD, auto
            else:
                psm_options = [psm]
            
            # OCR Engine Mode
            if oem is None:
                oem = 3  # Default mode
            
            best_result = None
            best_confidence = 0.0
            
            # Try different PSM modes and pick the best one
            for psm_mode in psm_options:
                try:
                    # Enhanced Tesseract config for better results
                    config = f"--psm {psm_mode} --oem {oem} -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789@.,:/-() "
                    
                    # Extract text with confidence scores
                    data = pytesseract.image_to_data(image, lang=lang, config=config, 
                                                     output_type=pytesseract.Output.DICT)
                    
                    # Extract text with better configuration
                    raw_text = pytesseract.image_to_string(image, lang=lang, config=config)
                    
                    # Calculate average confidence
                    confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
                    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
                    
                    # Count non-empty words
                    words = [word for word in data['text'] if word.strip()]
                    word_count = len(words)
                    
                    # Score: confidence * word_count (more words with good confidence = better)
                    score = avg_confidence * (1 + word_count / 100)
                    
                    if score > best_confidence or best_result is None:
                        best_confidence = score
                        best_result = {
                            "raw_text": raw_text.strip(),
                            "confidence": round(avg_confidence, 2),
                            "word_count": word_count,
                            "psm_mode": psm_mode,
                            "structured_data": None,
                            "provider": self.get_provider_name()
                        }
                except Exception as e:
                    # If one PSM mode fails, try next
                    continue
            
            if best_result is None:
                # Fallback to basic extraction
                config = f"--psm 6 --oem {oem}"
                raw_text = pytesseract.image_to_string(image, lang=lang, config=config)
                data = pytesseract.image_to_data(image, lang=lang, config=config, 
                                                 output_type=pytesseract.Output.DICT)
                confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
                
                best_result = {
                    "raw_text": raw_text.strip(),
                    "confidence": round(avg_confidence, 2),
                    "word_count": len([w for w in data['text'] if w.strip()]),
                    "psm_mode": 6,
                    "structured_data": None,
                    "provider": self.get_provider_name()
                }
            
            if best_result:
                best_result.setdefault("pages_processed", 1)
                best_result.setdefault(
                    "page_results",
                    [
                        {
                            "page": 1,
                            "raw_text": best_result.get("raw_text", ""),
                            "confidence": best_result.get("confidence"),
                        }
                    ],
                )

            return best_result
            
        except FileNotFoundError as e:
            raise Exception(f"Tesseract OCR error: Tesseract not found. Please ensure Tesseract is installed and the path is configured correctly. Error: {str(e)}")
        except Exception as e:
            error_msg = str(e)
            if "tesseract" in error_msg.lower() and "not found" in error_msg.lower():
                raise Exception(f"Tesseract OCR error: Tesseract executable not found. Please install Tesseract OCR and ensure it's in your PATH or set TESSERACT_CMD environment variable.")
            raise Exception(f"Tesseract OCR error: {error_msg}")
    
    def is_available(self) -> bool:
        """Check if Tesseract is installed and available"""
        try:
            # Ensure path is configured before checking
            if platform.system() == "Windows":
                # First check if TESSERACT_CMD environment variable is set
                tesseract_cmd = os.environ.get('TESSERACT_CMD')
                if tesseract_cmd and os.path.exists(tesseract_cmd):
                    pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
                elif not hasattr(pytesseract.pytesseract, 'tesseract_cmd') or not pytesseract.pytesseract.tesseract_cmd:
                    # Try default installation paths
                    default_paths = [
                        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                    ]
                    for path in default_paths:
                        if os.path.exists(path):
                            pytesseract.pytesseract.tesseract_cmd = path
                            break
            
            pytesseract.get_tesseract_version()
            return True
        except Exception as e:
            return False
    
    def get_provider_name(self) -> str:
        return "tesseract"

