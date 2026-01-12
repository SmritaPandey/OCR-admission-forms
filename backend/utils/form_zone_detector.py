"""
Form Zone Detector - Detects logical zones in SRCC admission forms.

This module segments scanned forms into logical regions (zones) to enable
more accurate OCR extraction by processing each zone separately.
"""

import numpy as np
from PIL import Image
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)

# Try to import OpenCV, fall back gracefully if not available
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    logger.warning("OpenCV not available. Zone detection will use basic mode.")


@dataclass
class Zone:
    """Represents a detected zone in the form."""
    name: str
    x: int
    y: int
    width: int
    height: int
    page: int = 1
    fields: List[str] = field(default_factory=list)
    confidence: float = 1.0
    
    @property
    def x2(self) -> int:
        return self.x + self.width
    
    @property
    def y2(self) -> int:
        return self.y + self.height
    
    @property
    def bounds(self) -> Tuple[int, int, int, int]:
        """Return (x1, y1, x2, y2) bounds."""
        return (self.x, self.y, self.x2, self.y2)
    
    def contains_point(self, x: int, y: int) -> bool:
        """Check if a point is within this zone."""
        return self.x <= x <= self.x2 and self.y <= y <= self.y2
    
    def crop_from_image(self, image: Image.Image) -> Image.Image:
        """Crop this zone from the given image."""
        return image.crop(self.bounds)


# SRCC Form Zone Definitions (normalized coordinates 0-1)
# Based on the 4-page SRCC Student Data Form template
SRCC_ZONE_DEFINITIONS = {
    'page_1': {
        'header': {
            'x_range': (0.0, 1.0),
            'y_range': (0.0, 0.12),
            'fields': ['college_name', 'academic_session', 'course', 'category'],
            'description': 'Form header with college name, session, course selection'
        },
        'form_numbers': {
            'x_range': (0.0, 1.0),
            'y_range': (0.10, 0.18),
            'fields': ['du_portal_form_number', 'cuet_score', 'college_roll_no', 'date_of_admission'],
            'description': 'Form numbers row'
        },
        'photo': {
            'x_range': (0.78, 0.98),
            'y_range': (0.12, 0.32),
            'fields': ['photo'],
            'description': 'Passport photo area'
        },
        'student_name': {
            'x_range': (0.0, 0.75),
            'y_range': (0.18, 0.30),
            'fields': ['student_name', 'first_name', 'middle_name', 'surname'],
            'description': 'Student name section'
        },
        'personal_details': {
            'x_range': (0.0, 1.0),
            'y_range': (0.28, 0.42),
            'fields': ['gender', 'date_of_birth'],
            'description': 'Gender and DOB section'
        },
        'permanent_address': {
            'x_range': (0.0, 1.0),
            'y_range': (0.40, 0.55),
            'fields': ['permanent_address', 'permanent_state', 'pincode'],
            'description': 'Permanent address section'
        },
        'correspondence_address': {
            'x_range': (0.0, 1.0),
            'y_range': (0.53, 0.65),
            'fields': ['correspondence_address', 'correspondence_state', 'correspondence_pincode'],
            'description': 'Correspondence address section'
        },
        'contact_details': {
            'x_range': (0.0, 1.0),
            'y_range': (0.63, 0.72),
            'fields': ['email', 'phone_number'],
            'description': 'Email and phone section'
        },
        'parent_names': {
            'x_range': (0.0, 1.0),
            'y_range': (0.70, 0.80),
            'fields': ['mother_name', 'father_name'],
            'description': 'Parent names section'
        },
        'cuet_subjects': {
            'x_range': (0.0, 1.0),
            'y_range': (0.78, 0.98),
            'fields': ['cuet_subjects', 'cuet_scores'],
            'description': 'CUET subject scores table'
        },
    },
    'page_2': {
        'class_xii_details': {
            'x_range': (0.0, 1.0),
            'y_range': (0.0, 0.25),
            'fields': ['year_of_passing', 'board_university', 'exam_roll_no', 
                      'institution_last_attended', 'hindi_studied_upto'],
            'description': 'Class XII qualifying examination details'
        },
        'personal_info': {
            'x_range': (0.0, 1.0),
            'y_range': (0.23, 0.40),
            'fields': ['nationality', 'religion', 'blood_group', 
                      'below_poverty_line', 'annual_income', 'minority_status'],
            'description': 'Personal information section'
        },
        'mother_occupation': {
            'x_range': (0.0, 1.0),
            'y_range': (0.38, 0.52),
            'fields': ['mother_occupation', 'mother_designation', 
                      'mother_organization', 'mother_email', 'mother_phone'],
            'description': "Mother's occupational details"
        },
        'father_occupation': {
            'x_range': (0.0, 1.0),
            'y_range': (0.50, 0.64),
            'fields': ['father_occupation', 'father_designation',
                      'father_organization', 'father_email', 'father_phone'],
            'description': "Father's occupational details"
        },
        'guardian_details': {
            'x_range': (0.0, 1.0),
            'y_range': (0.62, 0.76),
            'fields': ['guardian_name', 'guardian_address', 
                      'guardian_organization', 'guardian_email', 'guardian_phone'],
            'description': "Local guardian's details"
        },
        'other_info': {
            'x_range': (0.0, 1.0),
            'y_range': (0.74, 0.85),
            'fields': ['du_enrollment_number', 'hindi_medium'],
            'description': 'Other information section'
        },
        'certificate_details': {
            'x_range': (0.0, 1.0),
            'y_range': (0.83, 0.98),
            'fields': ['certificate_authority', 'certificate_number', 
                      'certificate_date', 'disability_percentage', 'udid_number'],
            'description': 'Certificate details for reserved categories'
        },
    },
    'page_3': {
        'documents_checklist': {
            'x_range': (0.0, 1.0),
            'y_range': (0.0, 1.0),
            'fields': ['documents_attached'],
            'description': 'Documents checklist page'
        },
    },
    'page_4': {
        'student_declaration': {
            'x_range': (0.0, 1.0),
            'y_range': (0.0, 0.50),
            'fields': ['student_declaration', 'student_signature'],
            'description': 'Student declaration and signature'
        },
        'parent_declaration': {
            'x_range': (0.0, 1.0),
            'y_range': (0.48, 1.0),
            'fields': ['parent_declaration', 'parent_signature'],
            'description': 'Parent/Guardian declaration and signature'
        },
    },
}


class FormZoneDetector:
    """
    Detects logical zones in SRCC admission forms.
    
    Uses a combination of:
    1. Template-based zone definitions (known form layout)
    2. Line detection to find section boundaries
    3. Text density analysis to refine zones
    """
    
    def __init__(self, form_type: str = 'srcc'):
        """
        Initialize the zone detector.
        
        Args:
            form_type: Type of form to detect zones for ('srcc' is default)
        """
        self.form_type = form_type
        self.zone_definitions = SRCC_ZONE_DEFINITIONS
        
    def detect_zones(self, image: Image.Image, page_number: int = 1) -> List[Zone]:
        """
        Detect zones in a form image.
        
        Args:
            image: PIL Image of the form page
            page_number: Page number (1-4 for SRCC form)
            
        Returns:
            List of detected Zone objects
        """
        width, height = image.size
        page_key = f'page_{page_number}'
        
        # Get zone definitions for this page
        page_zones = self.zone_definitions.get(page_key, {})
        
        zones = []
        for zone_name, zone_def in page_zones.items():
            x_range = zone_def['x_range']
            y_range = zone_def['y_range']
            
            # Convert normalized coordinates to pixel coordinates
            x = int(x_range[0] * width)
            y = int(y_range[0] * height)
            zone_width = int((x_range[1] - x_range[0]) * width)
            zone_height = int((y_range[1] - y_range[0]) * height)
            
            zone = Zone(
                name=zone_name,
                x=x,
                y=y,
                width=zone_width,
                height=zone_height,
                page=page_number,
                fields=zone_def.get('fields', []),
                confidence=1.0
            )
            zones.append(zone)
        
        # If OpenCV is available, refine zones using line detection
        if CV2_AVAILABLE:
            zones = self._refine_zones_with_lines(image, zones)
        
        return zones
    
    def _refine_zones_with_lines(self, image: Image.Image, zones: List[Zone]) -> List[Zone]:
        """
        Refine zone boundaries using detected horizontal lines.
        
        Args:
            image: PIL Image
            zones: Initial zone list
            
        Returns:
            Refined zone list
        """
        try:
            # Convert PIL to OpenCV format
            cv_image = np.array(image)
            if len(cv_image.shape) == 3:
                gray = cv2.cvtColor(cv_image, cv2.COLOR_RGB2GRAY)
            else:
                gray = cv_image
            
            # Detect horizontal lines
            horizontal_lines = self._detect_horizontal_lines(gray)
            
            # Detect vertical lines (for column detection)
            vertical_lines = self._detect_vertical_lines(gray)
            
            # Refine zones based on detected lines
            # For now, we keep the template zones but can enhance with line info
            # This is a placeholder for more sophisticated zone refinement
            
            return zones
            
        except Exception as e:
            logger.warning(f"Zone refinement failed: {e}")
            return zones
    
    def _detect_horizontal_lines(self, gray: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        Detect horizontal lines in the image.
        
        Args:
            gray: Grayscale numpy array
            
        Returns:
            List of line coordinates (x1, y1, x2, y2)
        """
        if not CV2_AVAILABLE:
            return []
        
        try:
            # Threshold the image
            _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
            
            # Create horizontal kernel
            height, width = gray.shape
            horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (width // 20, 1))
            
            # Detect horizontal lines
            horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)
            
            # Find contours of horizontal lines
            contours, _ = cv2.findContours(horizontal, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            lines = []
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                # Only keep lines that span a significant portion of the width
                if w > width * 0.3:
                    lines.append((x, y, x + w, y + h))
            
            return sorted(lines, key=lambda l: l[1])  # Sort by y coordinate
            
        except Exception as e:
            logger.warning(f"Horizontal line detection failed: {e}")
            return []
    
    def _detect_vertical_lines(self, gray: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        Detect vertical lines in the image.
        
        Args:
            gray: Grayscale numpy array
            
        Returns:
            List of line coordinates (x1, y1, x2, y2)
        """
        if not CV2_AVAILABLE:
            return []
        
        try:
            # Threshold the image
            _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
            
            # Create vertical kernel
            height, width = gray.shape
            vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, height // 20))
            
            # Detect vertical lines
            vertical = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel, iterations=2)
            
            # Find contours of vertical lines
            contours, _ = cv2.findContours(vertical, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            lines = []
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                # Only keep lines that span a significant portion of the height
                if h > height * 0.1:
                    lines.append((x, y, x + w, y + h))
            
            return sorted(lines, key=lambda l: l[0])  # Sort by x coordinate
            
        except Exception as e:
            logger.warning(f"Vertical line detection failed: {e}")
            return []
    
    def get_zone_for_field(self, field_name: str, page_number: int = None) -> Optional[Dict]:
        """
        Get the zone definition for a specific field.
        
        Args:
            field_name: Name of the field to find
            page_number: Optional page number to search (searches all if None)
            
        Returns:
            Zone definition dict or None
        """
        pages_to_search = [f'page_{page_number}'] if page_number else self.zone_definitions.keys()
        
        for page_key in pages_to_search:
            page_zones = self.zone_definitions.get(page_key, {})
            for zone_name, zone_def in page_zones.items():
                if field_name in zone_def.get('fields', []):
                    return {
                        'zone_name': zone_name,
                        'page': int(page_key.split('_')[1]),
                        **zone_def
                    }
        
        return None
    
    def get_fields_in_zone(self, zone_name: str, page_number: int) -> List[str]:
        """
        Get all field names in a specific zone.
        
        Args:
            zone_name: Name of the zone
            page_number: Page number
            
        Returns:
            List of field names
        """
        page_key = f'page_{page_number}'
        zone_def = self.zone_definitions.get(page_key, {}).get(zone_name, {})
        return zone_def.get('fields', [])
    
    def extract_zone_images(self, image: Image.Image, page_number: int = 1) -> Dict[str, Image.Image]:
        """
        Extract cropped images for each zone.
        
        Args:
            image: PIL Image of the form page
            page_number: Page number
            
        Returns:
            Dictionary mapping zone names to cropped images
        """
        zones = self.detect_zones(image, page_number)
        zone_images = {}
        
        for zone in zones:
            try:
                cropped = zone.crop_from_image(image)
                zone_images[zone.name] = cropped
            except Exception as e:
                logger.warning(f"Failed to crop zone {zone.name}: {e}")
        
        return zone_images
    
    def get_reading_order(self, page_number: int = 1) -> List[str]:
        """
        Get the recommended reading order for zones on a page.
        
        Args:
            page_number: Page number
            
        Returns:
            List of zone names in reading order (top to bottom, left to right)
        """
        page_key = f'page_{page_number}'
        page_zones = self.zone_definitions.get(page_key, {})
        
        # Sort zones by y_range start, then x_range start
        sorted_zones = sorted(
            page_zones.items(),
            key=lambda x: (x[1]['y_range'][0], x[1]['x_range'][0])
        )
        
        return [zone_name for zone_name, _ in sorted_zones]


def detect_form_zones(image: Image.Image, page_number: int = 1, form_type: str = 'srcc') -> List[Zone]:
    """
    Convenience function to detect zones in a form image.
    
    Args:
        image: PIL Image of the form page
        page_number: Page number (1-indexed)
        form_type: Type of form
        
    Returns:
        List of Zone objects
    """
    detector = FormZoneDetector(form_type=form_type)
    return detector.detect_zones(image, page_number)


def get_zone_for_field(field_name: str, form_type: str = 'srcc') -> Optional[Dict]:
    """
    Get zone information for a specific field.
    
    Args:
        field_name: Name of the field
        form_type: Type of form
        
    Returns:
        Zone definition or None
    """
    detector = FormZoneDetector(form_type=form_type)
    return detector.get_zone_for_field(field_name)
