"""
Combined Tesseract + Google Vision OCR Provider

This provider combines the strengths of both tools:
- Tesseract: Excellent layout detection (identifies text regions)
- Google Vision: Superior character recognition (especially for complex/historical fonts)

Implementation based on Programming Historian lesson:
https://programminghistorian.org/en/lessons/ocr-with-google-vision-and-tesseract

Method: Coordinate matching - Uses Tesseract to identify text regions, then extracts
words from Google Vision's detailed response that fall within those regions.
"""
from typing import Dict, Any, Optional, List, Tuple
from PIL import Image
import pytesseract
from google.cloud import vision
import io
from backend.ocr.base_provider import OCRProvider
from backend.config import settings
from backend.ocr.google_vision_provider import GoogleVisionProvider
from backend.utils.image_preprocessing import enhance_for_ocr


class TesseractGoogleCombinedProvider(OCRProvider):
    """
    Combined OCR provider using Tesseract for layout detection
    and Google Vision for character recognition.
    
    Best for: Documents with complex layouts (columns, tables) and
    challenging characters (historical fonts, diacritics, ligatures).
    """
    
    def __init__(self):
        self.name = "tesseract-google-combined"
        self.google_vision_provider = GoogleVisionProvider()
        self._google_client = None
    
    def _get_google_client(self):
        """Initialize and return Google Vision client"""
        if self._google_client is None:
            self._google_client = self.google_vision_provider._get_client()
        return self._google_client
    
    def _get_tesseract_regions(self, image: Image.Image, psm: int = 6) -> List[Dict[str, int]]:
        """
        Use Tesseract to identify text regions in the image.
        
        Args:
            image: PIL Image to process
            psm: Page Segmentation Mode (6 = uniform block, 4 = single column)
            
        Returns:
            List of dictionaries with region coordinates: [{'x': int, 'y': int, 'w': int, 'h': int}, ...]
        """
        try:
            # Use pytesseract to get layout information
            # PSM 6 = Assume uniform block of text (good for forms)
            # PSM 4 = Assume single column
            data = pytesseract.image_to_data(
                image, 
                config=f'--psm {psm}',
                output_type=pytesseract.Output.DICT
            )
            
            # Group words into regions based on proximity
            regions = []
            words_with_coords = []
            
            # Collect all words with their bounding boxes
            for i in range(len(data['text'])):
                text = data['text'][i].strip()
                if text and int(data['conf'][i]) > 0:
                    x = data['left'][i]
                    y = data['top'][i]
                    w = data['width'][i]
                    h = data['height'][i]
                    words_with_coords.append({
                        'x': x, 'y': y, 'w': w, 'h': h,
                        'text': text
                    })
            
            if not words_with_coords:
                # Fallback: return full image as single region
                width, height = image.size
                return [{'x': 0, 'y': 0, 'w': width, 'h': height}]
            
            # Group words into regions using bounding box clustering
            regions = self._cluster_words_into_regions(words_with_coords, image.size)
            
            return regions
            
        except Exception as e:
            # Fallback: return full image as single region
            width, height = image.size
            return [{'x': 0, 'y': 0, 'w': width, 'h': height}]
    
    def _cluster_words_into_regions(self, words: List[Dict], image_size: Tuple[int, int]) -> List[Dict[str, int]]:
        """
        Cluster words into regions based on proximity.
        
        Args:
            words: List of word dictionaries with x, y, w, h
            image_size: (width, height) tuple
            
        Returns:
            List of region dictionaries with x, y, w, h
        """
        if not words:
            return []
        
        # Simple approach: group words by vertical proximity (for columns)
        # Sort words by y-coordinate (top to bottom)
        sorted_words = sorted(words, key=lambda w: (w['y'], w['x']))
        
        regions = []
        current_region_words = [sorted_words[0]]
        
        # Threshold for vertical spacing (pixels) - words closer than this are in same region
        vertical_threshold = 30
        
        for word in sorted_words[1:]:
            # Check if word is close to current region
            last_word = current_region_words[-1]
            vertical_gap = word['y'] - (last_word['y'] + last_word['h'])
            
            if vertical_gap < vertical_threshold:
                # Add to current region
                current_region_words.append(word)
            else:
                # Finalize current region and start new one
                regions.append(self._words_to_region(current_region_words))
                current_region_words = [word]
        
        # Add last region
        if current_region_words:
            regions.append(self._words_to_region(current_region_words))
        
        return regions
    
    def _words_to_region(self, words: List[Dict]) -> Dict[str, int]:
        """Convert a list of words into a bounding box region"""
        if not words:
            return {'x': 0, 'y': 0, 'w': 0, 'h': 0}
        
        min_x = min(w['x'] for w in words)
        min_y = min(w['y'] for w in words)
        max_x = max(w['x'] + w['w'] for w in words)
        max_y = max(w['y'] + w['h'] for w in words)
        
        return {
            'x': max(0, min_x - 5),  # Add small padding
            'y': max(0, min_y - 5),
            'w': max_x - min_x + 10,
            'h': max_y - min_y + 10
        }
    
    def _get_google_vision_words(self, image: Image.Image) -> Dict[str, Any]:
        """
        Get word-level text and coordinates from Google Vision using DOCUMENT_TEXT_DETECTION.
        
        Args:
            image: PIL Image to process
            
        Returns:
            Dictionary with full text annotation including word-level bounding boxes
        """
        try:
            client = self._get_google_client()
            
            # Convert PIL Image to bytes
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            
            # Create image object for Vision API
            vision_image = vision.Image(content=img_byte_arr.getvalue())
            
            # Use document_text_detection for detailed layout information
            response = client.document_text_detection(image=vision_image)
            
            if not response.full_text_annotation:
                return {
                    'full_text': '',
                    'pages': []
                }
            
            # Extract full text annotation with word-level coordinates
            full_text_annotation = response.full_text_annotation
            
            # Parse pages, blocks, paragraphs, words
            pages_data = []
            for page in full_text_annotation.pages:
                page_words = []
                for block in page.blocks:
                    for paragraph in block.paragraphs:
                        for word in paragraph.words:
                            # Extract word text
                            word_text = ''.join([
                                symbol.text for symbol in word.symbols
                            ])
                            
                            # Get bounding box (pixel coordinates)
                            vertices = word.bounding_box.vertices
                            word_data = {
                                'text': word_text,
                                'vertices': [
                                    {'x': v.x if v.x is not None else 0, 'y': v.y if v.y is not None else 0}
                                    for v in vertices
                                ],
                                'confidence': word.confidence if hasattr(word, 'confidence') and word.confidence else 0.95
                            }
                            page_words.append(word_data)
                
                pages_data.append({
                    'width': page.width,
                    'height': page.height,
                    'words': page_words
                })
            
            return {
                'full_text': full_text_annotation.text,
                'pages': pages_data
            }
            
        except Exception as e:
            raise Exception(f"Google Vision document text detection error: {str(e)}")
    
    def _word_in_region(self, word_vertices: List[Dict], region: Dict[str, int], 
                       page_width: int, page_height: int, tolerance: int = 10) -> bool:
        """
        Check if a word (from Google Vision) falls within a region (from Tesseract).
        
        Args:
            word_vertices: List of vertex dicts with 'x', 'y' (pixel coordinates)
            region: Dict with 'x', 'y', 'w', 'h' (pixel coordinates)
            page_width: Width of page in pixels (for reference, may not be needed)
            page_height: Height of page in pixels (for reference, may not be needed)
            tolerance: Pixel tolerance for coordinate matching
            
        Returns:
            True if word center or significant portion is in region
        """
        if not word_vertices:
            return False
        
        # Calculate word bounding box in pixels (vertices are already in pixels)
        word_min_x = min(v['x'] for v in word_vertices)
        word_max_x = max(v['x'] for v in word_vertices)
        word_min_y = min(v['y'] for v in word_vertices)
        word_max_y = max(v['y'] for v in word_vertices)
        
        # Calculate word center
        word_center_x = (word_min_x + word_max_x) / 2
        word_center_y = (word_min_y + word_max_y) / 2
        
        # Region bounds
        region_min_x = region['x']
        region_max_x = region['x'] + region['w']
        region_min_y = region['y']
        region_max_y = region['y'] + region['h']
        
        # Check if word center is in region (with tolerance)
        center_in_region = (
            region_min_x - tolerance <= word_center_x <= region_max_x + tolerance and
            region_min_y - tolerance <= word_center_y <= region_max_y + tolerance
        )
        
        # Check overlap (more robust - checks if boxes overlap at all)
        overlap = (
            word_min_x < region_max_x and word_max_x > region_min_x and
            word_min_y < region_max_y and word_max_y > region_min_y
        )
        
        return center_in_region or overlap
    
    async def extract_text(self, image: Image.Image, language: Optional[str] = None,
                          preprocess: bool = True) -> Dict[str, Any]:
        """
        Extract text by combining Tesseract layout detection with Google Vision character recognition.
        
        Args:
            image: PIL Image to process
            language: Optional language code (passed to Tesseract)
            preprocess: Apply image preprocessing
            
        Returns:
            Dictionary with OCR result
        """
        try:
            # Validate inputs
            if image is None:
                raise ValueError("Image object is None")
            
            # Ensure image is in RGB mode
            if image.mode not in ('RGB', 'L', '1'):
                image = image.convert('RGB')
            
            # Preprocess if requested
            if preprocess:
                image = enhance_for_ocr(image)
            
            # Step 1: Get text regions from Tesseract
            tesseract_regions = self._get_tesseract_regions(image, psm=6)
            
            if not tesseract_regions:
                # Fallback: use full image as single region
                width, height = image.size
                tesseract_regions = [{'x': 0, 'y': 0, 'w': width, 'h': height}]
            
            # Step 2: Get word-level data from Google Vision
            google_data = self._get_google_vision_words(image)
            
            if not google_data.get('pages'):
                # Fallback: use Google Vision's full text directly
                return {
                    "raw_text": google_data.get('full_text', ''),
                    "confidence": 85.0,
                    "structured_data": None,
                    "provider": self.get_provider_name(),
                    "method": "google_vision_fallback"
                }
            
            # Step 3: Match Google Vision words to Tesseract regions
            page_data = google_data['pages'][0] if google_data['pages'] else None
            if not page_data:
                # Fallback: use Google Vision's full text directly
                return {
                    "raw_text": google_data.get('full_text', ''),
                    "confidence": 85.0,
                    "structured_data": None,
                    "provider": self.get_provider_name(),
                    "method": "google_vision_fallback"
                }
            
            # Get page dimensions (Google Vision provides these, but fallback to image size)
            page_width = page_data.get('width', image.size[0])
            page_height = page_data.get('height', image.size[1])
            
            # Sort regions by position (top to bottom, left to right)
            sorted_regions = sorted(tesseract_regions, key=lambda r: (r['y'], r['x']))
            
            # Extract text for each region
            region_texts = []
            all_confidences = []
            
            for region in sorted_regions:
                region_words = []
                
                # Find words that fall within this region
                for word_data in page_data['words']:
                    if self._word_in_region(
                        word_data['vertices'],
                        region,
                        page_width,
                        page_height
                    ):
                        region_words.append(word_data)
                
                # Sort words within region by position
                region_words.sort(key=lambda w: (
                    min(v['y'] for v in w['vertices']),
                    min(v['x'] for v in w['vertices'])
                ))
                
                # Build text for this region
                region_text = ' '.join([w['text'] for w in region_words])
                if region_text:
                    region_texts.append(region_text)
                    # Collect confidences
                    confidences = [w.get('confidence', 0.95) for w in region_words]
                    if confidences:
                        all_confidences.extend(confidences)
            
            # Combine all region texts
            combined_text = '\n'.join(region_texts) if region_texts else google_data.get('full_text', '')
            
            # Calculate average confidence
            avg_confidence = (
                sum(all_confidences) / len(all_confidences) * 100
                if all_confidences
                else 90.0
            )
            
            return {
                "raw_text": combined_text.strip(),
                "confidence": round(avg_confidence, 2),
                "structured_data": {
                    "regions_detected": len(tesseract_regions),
                    "method": "tesseract_layout_google_vision_text"
                },
                "provider": self.get_provider_name()
            }
            
        except Exception as e:
            # Fallback to Google Vision alone on error
            try:
                result = await self.google_vision_provider.extract_text(image, language)
                result["provider"] = self.get_provider_name()
                result["method"] = "google_vision_fallback_on_error"
                return result
            except:
                raise Exception(f"Combined OCR error: {str(e)}")
    
    def is_available(self) -> bool:
        """Check if both Tesseract and Google Vision are available"""
        try:
            # Check Tesseract
            pytesseract.get_tesseract_version()
            
            # Check Google Vision
            return self.google_vision_provider.is_available()
        except Exception:
            return False
    
    def get_provider_name(self) -> str:
        return "tesseract-google-combined"
