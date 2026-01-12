"""
Enhanced checkbox detection for SRCC form multiple choice fields
Specifically handles: Course, Admission Category, Gender, etc.

Uses multiple detection strategies:
1. OCR text pattern matching (checkbox marks in text)
2. Pixel density analysis (filled vs empty boxes)
3. Template matching (compare against empty checkbox template)
4. Context-aware selection (based on surrounding text)
"""
import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from PIL import Image

logger = logging.getLogger(__name__)

# Try to import NumPy and OpenCV for image-based detection
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False


class EnhancedCheckboxDetector:
    """
    Enhanced checkbox/radio button detector using multiple strategies.
    
    Strategies:
    1. Text-based: Look for check marks (✓, X, ☑) in OCR text
    2. Image-based: Analyze pixel density in checkbox regions
    3. Context-based: Infer selection from field position and surrounding text
    """
    
    # Checkbox detection thresholds
    FILL_RATIO_THRESHOLD = 0.15  # Minimum fill ratio to consider box checked
    MIN_CHECKBOX_SIZE = 15  # Minimum size in pixels
    MAX_CHECKBOX_SIZE = 50  # Maximum size in pixels
    
    def __init__(self):
        self.text_detector = SRCCCheckboxDetector()
    
    def detect_from_image(
        self, 
        image: Image.Image, 
        field_name: str,
        options: List[str],
        region: Optional[Tuple[int, int, int, int]] = None
    ) -> Optional[str]:
        """
        Detect selected option from checkbox/radio button in image.
        
        Args:
            image: PIL Image containing the checkboxes
            field_name: Name of the field (e.g., 'gender', 'category')
            options: List of option labels
            region: Optional (x, y, width, height) to crop
            
        Returns:
            Selected option label or None
        """
        if not CV2_AVAILABLE or not NUMPY_AVAILABLE:
            logger.debug("Image-based checkbox detection not available")
            return None
        
        try:
            # Crop to region if specified
            if region:
                x, y, w, h = region
                image = image.crop((x, y, x + w, y + h))
            
            # Convert to OpenCV format
            cv_image = np.array(image)
            if len(cv_image.shape) == 3:
                gray = cv2.cvtColor(cv_image, cv2.COLOR_RGB2GRAY)
            else:
                gray = cv_image
            
            # Find checkbox regions
            checkboxes = self._find_checkbox_regions(gray)
            
            if not checkboxes:
                return None
            
            # Analyze each checkbox for fill level
            results = []
            for i, (cx, cy, cw, ch) in enumerate(checkboxes):
                fill_ratio = self._calculate_fill_ratio(gray, cx, cy, cw, ch)
                is_checked = fill_ratio > self.FILL_RATIO_THRESHOLD
                
                # Map to option by position (assuming horizontal layout)
                if i < len(options):
                    results.append({
                        'option': options[i],
                        'checked': is_checked,
                        'fill_ratio': fill_ratio,
                        'position': (cx, cy)
                    })
            
            # Return the checked option with highest fill ratio
            checked = [r for r in results if r['checked']]
            if checked:
                best = max(checked, key=lambda x: x['fill_ratio'])
                return best['option']
            
            return None
            
        except Exception as e:
            logger.warning(f"Image checkbox detection failed: {e}")
            return None
    
    def _find_checkbox_regions(self, gray: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Find checkbox/radio button regions in grayscale image."""
        if not CV2_AVAILABLE:
            return []
        
        try:
            # Threshold to binary
            _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
            
            # Find contours
            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, 
                                           cv2.CHAIN_APPROX_SIMPLE)
            
            checkboxes = []
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                
                # Filter by size and aspect ratio
                if (self.MIN_CHECKBOX_SIZE <= w <= self.MAX_CHECKBOX_SIZE and
                    self.MIN_CHECKBOX_SIZE <= h <= self.MAX_CHECKBOX_SIZE):
                    aspect_ratio = w / h if h > 0 else 0
                    # Checkboxes are roughly square
                    if 0.7 <= aspect_ratio <= 1.3:
                        checkboxes.append((x, y, w, h))
            
            # Sort by x position (left to right)
            checkboxes.sort(key=lambda c: c[0])
            
            return checkboxes
            
        except Exception as e:
            logger.warning(f"Checkbox region detection failed: {e}")
            return []
    
    def _calculate_fill_ratio(
        self, 
        gray: np.ndarray, 
        x: int, y: int, w: int, h: int
    ) -> float:
        """Calculate the fill ratio of a checkbox region."""
        if not NUMPY_AVAILABLE:
            return 0.0
        
        try:
            # Extract checkbox region
            region = gray[y:y+h, x:x+w]
            
            # Count dark pixels (potential marks)
            dark_threshold = 150
            dark_pixels = np.sum(region < dark_threshold)
            total_pixels = region.size
            
            # Account for the checkbox border (exclude outer edge)
            border = 3
            if w > border * 2 and h > border * 2:
                inner_region = gray[y+border:y+h-border, x+border:x+w-border]
                dark_pixels = np.sum(inner_region < dark_threshold)
                total_pixels = inner_region.size
            
            return dark_pixels / total_pixels if total_pixels > 0 else 0.0
            
        except Exception as e:
            logger.warning(f"Fill ratio calculation failed: {e}")
            return 0.0
    
    def detect_from_text(self, text: str, field_name: str) -> Optional[str]:
        """
        Detect selected option from OCR text patterns.
        
        Uses multiple text patterns to identify checked options.
        """
        return self.text_detector.detect_field_from_text(text, field_name)
    
    def detect_with_context(
        self, 
        text: str, 
        field_name: str,
        image: Optional[Image.Image] = None,
        region: Optional[Tuple[int, int, int, int]] = None
    ) -> Dict[str, Any]:
        """
        Detect checkbox selection using all available methods.
        
        Combines text-based and image-based detection for best accuracy.
        
        Returns:
            Dict with 'value', 'confidence', 'method' keys
        """
        results = []
        
        # Try text-based detection
        text_result = self.detect_from_text(text, field_name)
        if text_result:
            results.append({
                'value': text_result,
                'confidence': 0.7,
                'method': 'text_pattern'
            })
        
        # Try image-based detection if available
        if image is not None:
            options = self._get_options_for_field(field_name)
            if options:
                image_result = self.detect_from_image(image, field_name, options, region)
                if image_result:
                    results.append({
                        'value': image_result,
                        'confidence': 0.85,
                        'method': 'image_analysis'
                    })
        
        # Try context-based detection from text
        context_result = self._detect_from_context(text, field_name)
        if context_result:
            results.append({
                'value': context_result,
                'confidence': 0.6,
                'method': 'context'
            })
        
        # Return highest confidence result
        if results:
            best = max(results, key=lambda x: x['confidence'])
            return best
        
        return {'value': None, 'confidence': 0.0, 'method': None}
    
    def _get_options_for_field(self, field_name: str) -> List[str]:
        """Get valid options for a checkbox field."""
        field_options = {
            'gender': ['Male', 'Female', 'Transgender'],
            'category': ['GEN', 'OBC', 'SC', 'ST', 'EWS', 'PwD', 'Sports', 'Foreign', 'CW', 'KM', 'Others', 'ECA'],
            'course': ['B.COM.(H)', 'B.A.(H) ECO'],
            'hindi_medium': ['Yes', 'No'],
            'below_poverty_line': ['Yes', 'No'],
            'hindi_studied_upto': ['VIII', 'X', 'XII', 'Never'],
        }
        return field_options.get(field_name, [])
    
    def _detect_from_context(self, text: str, field_name: str) -> Optional[str]:
        """
        Detect selection from context patterns in text.
        
        Looks for patterns like:
        - "Gender: Male" 
        - "Category: GEN"
        - Option appearing right after the field label
        """
        options = self._get_options_for_field(field_name)
        if not options:
            return None
        
        text_lower = text.lower()
        
        # Build regex patterns for each option
        for option in options:
            option_lower = option.lower()
            patterns = [
                # Field: Option pattern
                rf'{field_name}[:\s]+{re.escape(option_lower)}',
                # Option appears after field label on same or next line
                rf'{field_name}[^a-z]*\n[^a-z]*{re.escape(option_lower)}',
                # Just the option appearing prominently
                rf'\b{re.escape(option_lower)}\s*(?:✓|✔|☑|\[x\])',
            ]
            
            for pattern in patterns:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    return option
        
        return None


class SRCCCheckboxDetector:
    """Enhanced checkbox detector for SRCC Student Data Form"""
    
    # Mapping of checkbox labels to form fields
    CHECKBOX_MAPPINGS = {
        # Course checkboxes
        'course': {
            'b.com.(h)': 'B.COM.(H)',
            'b.a.(h) eco': 'B.A.(H) ECO',
        },
        # Gender checkboxes
        'gender': {
            'male': 'Male',
            'female': 'Female',
            'transgender': 'Transgender',
        },
        # Admission Category checkboxes
        'admission_category': {
            'gen': 'GEN',
            'obc': 'OBC',
            'sc': 'SC',
            'st': 'ST',
            'sports': 'Sports',
            'pwd': 'PwD',
            'ews': 'EWS',
            'foreign': 'Foreign',
            'cw': 'CW',
            'km': 'KM',
            'others': 'Others',
            'eca': 'ECA',
        },
        # Minority checkboxes
        'minority': {
            'muslim': 'Muslim',
            'jain': 'Jain',
            'sikh': 'Sikh',
            'persian': 'Persian',
            'christian': 'Christian',
            'buddhists': 'Buddhists',
            'others': 'Others',
        },
        # Hindi medium checkbox
        'hindi_medium': {
            'yes': 'Yes',
            'no': 'No',
        },
    }
    
    def detect_checkboxes_in_text(self, text: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Detect all checkboxes in OCR text and map them to form fields
        
        Returns:
            Dictionary mapping field names to list of detected checkboxes
        """
        results = {
            'course': [],
            'gender': [],
            'admission_category': [],
            'minority': [],
            'hindi_medium': [],
        }
        
        lines = text.split('\n')
        text_lower = text.lower()
        
        # Detect checkboxes for each category
        for category, options in self.CHECKBOX_MAPPINGS.items():
            for option_key, option_label in options.items():
                # Look for the option label near checkbox patterns
                checkbox_info = self._find_checkbox_for_option(
                    text, text_lower, lines, option_label, option_key, category
                )
                if checkbox_info:
                    results[category].append(checkbox_info)
        
        return results
    
    def _find_checkbox_for_option(
        self, 
        text: str, 
        text_lower: str, 
        lines: List[str],
        option_label: str,
        option_key: str,
        category: str
    ) -> Optional[Dict[str, Any]]:
        """Find if a checkbox is checked for a specific option"""
        
        # Normalize option label for searching
        option_variations = [
            option_label.lower(),
            option_key,
            option_label.replace('.', '').lower(),
            option_label.replace('(', '').replace(')', '').lower(),
        ]
        
        # Search for checkbox patterns near the option label
        for i, line in enumerate(lines):
            line_lower = line.lower()
            
            # Check if this line contains the option label
            contains_option = any(var in line_lower for var in option_variations)
            if not contains_option:
                continue
            
            # Look for checkbox patterns on this line or nearby lines
            checked_patterns = [
                r'[xX]',           # X mark
                r'✓',              # Check mark
                r'✔',              # Heavy check mark
                r'☑',              # Ballot box with check
                r'■',              # Filled square
                r'\[[xX✓✔☑]\]',   # [x], [X], [✓], etc.
                r'\([xX✓✔☑]\)',   # (x), (X), (✓), etc.
                r'☐[xX✓✔☑]',      # ☐x, ☐X, etc.
            ]
            
            # Check for checked checkbox
            is_checked = False
            for pattern in checked_patterns:
                if re.search(pattern, line):
                    is_checked = True
                    break
            
            # Also check previous/next line if checkbox might be on separate line
            if not is_checked:
                for offset in [-1, 1]:
                    if 0 <= i + offset < len(lines):
                        nearby_line = lines[i + offset]
                        for pattern in checked_patterns:
                            if re.search(pattern, nearby_line):
                                # Verify the option is nearby
                                if any(var in line_lower or var in nearby_line.lower() for var in option_variations):
                                    is_checked = True
                                    break
                        if is_checked:
                            break
            
            if is_checked:
                return {
                    'label': option_label,
                    'checked': True,
                    'category': category,
                    'value': option_label,
                    'confidence': 0.8,
                    'line': i + 1,
                }
        
        return None
    
    def extract_form_fields_from_checkboxes(
        self, 
        checkbox_results: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        Extract form field values from detected checkboxes
        
        For single-select fields (course, gender), returns the checked value.
        For multi-select fields (admission_category, minority), returns list or comma-separated string.
        """
        extracted = {}
        
        # Course (single select)
        if checkbox_results['course']:
            checked = [cb for cb in checkbox_results['course'] if cb.get('checked')]
            if checked:
                extracted['course_applied'] = checked[0]['value']
        
        # Gender (single select)
        if checkbox_results['gender']:
            checked = [cb for cb in checkbox_results['gender'] if cb.get('checked')]
            if checked:
                extracted['gender'] = checked[0]['value']
        
        # Admission Category (single select, but "Others" might have additional text)
        if checkbox_results['admission_category']:
            checked = [cb for cb in checkbox_results['admission_category'] if cb.get('checked')]
            if checked:
                extracted['category'] = checked[0]['value']
                # If "Others" is checked, look for specification
                if checked[0]['value'].lower() == 'others':
                    # This will be handled separately in form parser
                    pass
        
        # Minority (can be multiple)
        if checkbox_results['minority']:
            checked = [cb for cb in checkbox_results['minority'] if cb.get('checked')]
            if checked:
                extracted['minority'] = ', '.join([cb['value'] for cb in checked])
        
        # Hindi Medium (single select)
        if checkbox_results['hindi_medium']:
            checked = [cb for cb in checkbox_results['hindi_medium'] if cb.get('checked')]
            if checked:
                extracted['hindi_medium'] = checked[0]['value'] == 'Yes'
        
        return extracted
    
    def detect_field_from_text(self, text: str, field_name: str) -> Optional[str]:
        """
        Detect a specific checkbox field value from OCR text.
        
        Args:
            text: OCR text to analyze
            field_name: Name of the field (gender, category, course, etc.)
            
        Returns:
            Selected option value or None
        """
        # Map field names to category names
        field_to_category = {
            'gender': 'gender',
            'category': 'admission_category',
            'admission_category': 'admission_category',
            'course': 'course',
            'course_applied': 'course',
            'minority': 'minority',
            'hindi_medium': 'hindi_medium',
        }
        
        category = field_to_category.get(field_name)
        if not category:
            return None
        
        # Run checkbox detection
        checkbox_results = self.detect_checkboxes_in_text(text)
        
        # Get checked options for this category
        category_results = checkbox_results.get(category, [])
        checked = [cb for cb in category_results if cb.get('checked')]
        
        if checked:
            return checked[0]['value']
        
        # Fallback: Try to find the value using context patterns
        options = self.CHECKBOX_MAPPINGS.get(category, {})
        text_lower = text.lower()
        
        for option_key, option_label in options.items():
            # Look for the option appearing after the field label
            patterns = [
                rf'{field_name}[:\s]+{re.escape(option_label)}',
                rf'{field_name}[:\s]+{re.escape(option_key)}',
                rf'\b{re.escape(option_label)}\b.*?(?:✓|✔|☑|selected|checked)',
            ]
            
            for pattern in patterns:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    return option_label
        
        return None


# Integration function to use in form parser
def extract_checkbox_fields_from_text(text: str) -> Dict[str, Any]:
    """
    Extract checkbox-based fields from OCR text
    """
    detector = SRCCCheckboxDetector()
    checkbox_results = detector.detect_checkboxes_in_text(text)
    return detector.extract_form_fields_from_checkboxes(checkbox_results)


def detect_checkbox_field(
    text: str, 
    field_name: str, 
    image: Optional[Image.Image] = None,
    region: Optional[Tuple[int, int, int, int]] = None
) -> Dict[str, Any]:
    """
    Detect a checkbox field value using all available methods.
    
    Args:
        text: OCR text containing the field
        field_name: Name of the checkbox field
        image: Optional image for image-based detection
        region: Optional region to crop from image
        
    Returns:
        Dict with 'value', 'confidence', 'method' keys
    """
    detector = EnhancedCheckboxDetector()
    return detector.detect_with_context(text, field_name, image, region)


def extract_all_checkbox_fields(
    text: str,
    image: Optional[Image.Image] = None
) -> Dict[str, Any]:
    """
    Extract all checkbox-based fields from form.
    
    Uses enhanced detection combining text and image analysis.
    
    Args:
        text: OCR text from the form
        image: Optional form image for visual analysis
        
    Returns:
        Dictionary of field names to extracted values
    """
    detector = EnhancedCheckboxDetector()
    
    # Fields that use checkboxes/radio buttons
    checkbox_fields = ['gender', 'category', 'course', 'hindi_medium', 'below_poverty_line']
    
    results = {}
    for field in checkbox_fields:
        result = detector.detect_with_context(text, field, image)
        if result.get('value'):
            results[field] = result['value']
            results[f'{field}_confidence'] = result.get('confidence', 0.0)
    
    return results

