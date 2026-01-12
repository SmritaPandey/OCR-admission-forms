"""
Template-Based Field Mapping - Uses empty form template to locate field positions.

This module:
1. Analyzes the empty SRCC form template to identify field regions
2. Matches filled forms against the template
3. Extracts values from specific field regions
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from PIL import Image

logger = logging.getLogger(__name__)

# Try to import OpenCV and NumPy
try:
    import numpy as np
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    logger.warning("OpenCV not available. Template matching will use basic mode.")


@dataclass
class FieldRegion:
    """Represents a field region in the form template."""
    name: str
    x: int
    y: int
    width: int
    height: int
    page: int = 1
    field_type: str = 'text'  # text, checkbox, date, number
    description: str = ''
    
    @property
    def bounds(self) -> Tuple[int, int, int, int]:
        """Return (x1, y1, x2, y2) bounds."""
        return (self.x, self.y, self.x + self.width, self.y + self.height)
    
    def scale(self, scale_x: float, scale_y: float) -> 'FieldRegion':
        """Return a scaled copy of this region."""
        return FieldRegion(
            name=self.name,
            x=int(self.x * scale_x),
            y=int(self.y * scale_y),
            width=int(self.width * scale_x),
            height=int(self.height * scale_y),
            page=self.page,
            field_type=self.field_type,
            description=self.description
        )


# ==============================================================================
# SRCC Form Field Regions (based on empty template analysis)
# Coordinates are for a standard A4 scan at ~1700x2400 pixels
# ==============================================================================

SRCC_FIELD_REGIONS = {
    # Page 1 - Header and Basic Info
    'page_1': {
        # Header row
        'academic_session': FieldRegion(
            name='academic_session',
            x=450, y=80, width=200, height=30,
            page=1, field_type='text',
            description='Academic Session 2024-25'
        ),
        'course_bcom': FieldRegion(
            name='course_bcom',
            x=200, y=120, width=30, height=30,
            page=1, field_type='checkbox',
            description='B.COM.(H) checkbox'
        ),
        'course_ba_eco': FieldRegion(
            name='course_ba_eco',
            x=350, y=120, width=30, height=30,
            page=1, field_type='checkbox',
            description='B.A.(H) ECO checkbox'
        ),
        
        # Form numbers row
        'du_portal_form_number': FieldRegion(
            name='du_portal_form_number',
            x=200, y=180, width=200, height=25,
            page=1, field_type='number',
            description='DU Portal Form Number (12 digits)'
        ),
        'cuet_score': FieldRegion(
            name='cuet_score',
            x=550, y=180, width=100, height=25,
            page=1, field_type='number',
            description='CUET Score'
        ),
        'college_roll_no': FieldRegion(
            name='college_roll_no',
            x=800, y=180, width=150, height=25,
            page=1, field_type='text',
            description='College Roll No.'
        ),
        'date_of_admission': FieldRegion(
            name='date_of_admission',
            x=1100, y=180, width=150, height=25,
            page=1, field_type='date',
            description='Date of Admission'
        ),
        
        # Photo area
        'photo': FieldRegion(
            name='photo',
            x=1350, y=200, width=300, height=400,
            page=1, field_type='photo',
            description='Passport Photo'
        ),
        
        # Student name section (Field 1)
        'student_name': FieldRegion(
            name='student_name',
            x=100, y=320, width=1200, height=60,
            page=1, field_type='text',
            description='Student Name in Block Letters'
        ),
        
        # Gender (Field 2)
        'gender': FieldRegion(
            name='gender',
            x=100, y=420, width=600, height=40,
            page=1, field_type='checkbox',
            description='Gender: Male/Female/Transgender'
        ),
        
        # Date of Birth (Field 3)
        'date_of_birth': FieldRegion(
            name='date_of_birth',
            x=100, y=480, width=300, height=40,
            page=1, field_type='date',
            description='Date of Birth'
        ),
        
        # Permanent Address (Field 4)
        'permanent_address': FieldRegion(
            name='permanent_address',
            x=100, y=550, width=1200, height=100,
            page=1, field_type='text',
            description='Permanent Address'
        ),
        'permanent_state': FieldRegion(
            name='permanent_state',
            x=100, y=650, width=300, height=30,
            page=1, field_type='text',
            description='State'
        ),
        'pincode': FieldRegion(
            name='pincode',
            x=450, y=650, width=150, height=30,
            page=1, field_type='number',
            description='PIN Code'
        ),
        
        # Correspondence Address (Field 5)
        'correspondence_address': FieldRegion(
            name='correspondence_address',
            x=100, y=720, width=1200, height=80,
            page=1, field_type='text',
            description='Local Address for Correspondence'
        ),
        
        # Email (Field 6)
        'email': FieldRegion(
            name='email',
            x=100, y=850, width=500, height=30,
            page=1, field_type='text',
            description='Email'
        ),
        
        # Contact Numbers (Field 7)
        'phone_number': FieldRegion(
            name='phone_number',
            x=700, y=850, width=200, height=30,
            page=1, field_type='number',
            description='Contact Number'
        ),
        
        # Mother's Name (Field 8)
        'mother_name': FieldRegion(
            name='mother_name',
            x=100, y=920, width=500, height=40,
            page=1, field_type='text',
            description="Mother's Name"
        ),
        
        # Father's Name (Field 9)
        'father_name': FieldRegion(
            name='father_name',
            x=700, y=920, width=500, height=40,
            page=1, field_type='text',
            description="Father's Name"
        ),
    },
    
    # Page 2 - Detailed Information
    'page_2': {
        # Class XII Details (Field 11)
        'year_of_passing': FieldRegion(
            name='year_of_passing',
            x=300, y=100, width=100, height=30,
            page=2, field_type='number',
            description='Year of Passing'
        ),
        'board_university': FieldRegion(
            name='board_university',
            x=500, y=100, width=400, height=30,
            page=2, field_type='text',
            description='Board/University'
        ),
        'exam_roll_no': FieldRegion(
            name='exam_roll_no',
            x=300, y=150, width=200, height=30,
            page=2, field_type='number',
            description='Examination Roll No.'
        ),
        'institution_last_attended': FieldRegion(
            name='institution_last_attended',
            x=300, y=200, width=600, height=30,
            page=2, field_type='text',
            description='Institution Last Attended'
        ),
        'hindi_studied_upto': FieldRegion(
            name='hindi_studied_upto',
            x=300, y=250, width=300, height=30,
            page=2, field_type='checkbox',
            description='Hindi studied upto: VIII/X/XII/Never'
        ),
        
        # Personal Information (Field 12)
        'nationality': FieldRegion(
            name='nationality',
            x=300, y=350, width=200, height=30,
            page=2, field_type='text',
            description='Nationality'
        ),
        'religion': FieldRegion(
            name='religion',
            x=600, y=350, width=200, height=30,
            page=2, field_type='text',
            description='Religion'
        ),
        'blood_group': FieldRegion(
            name='blood_group',
            x=900, y=350, width=100, height=30,
            page=2, field_type='text',
            description='Blood Group'
        ),
        'below_poverty_line': FieldRegion(
            name='below_poverty_line',
            x=300, y=400, width=150, height=30,
            page=2, field_type='checkbox',
            description='Below Poverty Line: Yes/No'
        ),
        'annual_income': FieldRegion(
            name='annual_income',
            x=500, y=400, width=200, height=30,
            page=2, field_type='number',
            description='Annual Income'
        ),
        
        # Mother's Occupational Details (Field 13)
        'mother_occupation': FieldRegion(
            name='mother_occupation',
            x=300, y=500, width=300, height=30,
            page=2, field_type='text',
            description="Mother's Occupation"
        ),
        'mother_phone': FieldRegion(
            name='mother_phone',
            x=700, y=550, width=200, height=30,
            page=2, field_type='number',
            description="Mother's Phone"
        ),
        
        # Father's Occupational Details (Field 14)
        'father_occupation': FieldRegion(
            name='father_occupation',
            x=300, y=650, width=300, height=30,
            page=2, field_type='text',
            description="Father's Occupation"
        ),
        'father_phone': FieldRegion(
            name='father_phone',
            x=700, y=700, width=200, height=30,
            page=2, field_type='number',
            description="Father's Phone"
        ),
        
        # Guardian Details (Field 15)
        'guardian_name': FieldRegion(
            name='guardian_name',
            x=300, y=800, width=400, height=30,
            page=2, field_type='text',
            description="Guardian's Name"
        ),
        'guardian_phone': FieldRegion(
            name='guardian_phone',
            x=700, y=850, width=200, height=30,
            page=2, field_type='number',
            description="Guardian's Phone"
        ),
        
        # Other Information (Field 16)
        'du_enrollment_number': FieldRegion(
            name='du_enrollment_number',
            x=450, y=950, width=200, height=30,
            page=2, field_type='number',
            description='DU Enrollment Number'
        ),
        'hindi_medium': FieldRegion(
            name='hindi_medium',
            x=800, y=950, width=150, height=30,
            page=2, field_type='checkbox',
            description='Hindi Medium: Yes/No'
        ),
    }
}


class TemplateFieldMapper:
    """
    Maps filled forms against empty template to locate field values.
    
    Uses template matching to align scanned forms with the template,
    then extracts values from known field regions.
    """
    
    def __init__(self, template_path: Optional[str] = None):
        """
        Initialize the template mapper.
        
        Args:
            template_path: Path to empty form template (optional)
        """
        self.template_path = template_path
        self.template_images: Dict[int, Image.Image] = {}
        self.field_regions = SRCC_FIELD_REGIONS
        
        if template_path:
            self._load_template()
    
    def _load_template(self):
        """Load template images from path."""
        try:
            from backend.utils.file_handler import load_all_pdf_pages
            
            pages = load_all_pdf_pages(self.template_path)
            for i, page in enumerate(pages, start=1):
                self.template_images[i] = page
                
            logger.info(f"Loaded {len(pages)} template pages")
            
        except Exception as e:
            logger.warning(f"Failed to load template: {e}")
    
    def get_field_regions(self, page_number: int = 1) -> Dict[str, FieldRegion]:
        """
        Get field regions for a specific page.
        
        Args:
            page_number: Page number (1-indexed)
            
        Returns:
            Dictionary of field name to FieldRegion
        """
        page_key = f'page_{page_number}'
        return self.field_regions.get(page_key, {})
    
    def get_region_for_field(self, field_name: str) -> Optional[FieldRegion]:
        """
        Get the region definition for a specific field.
        
        Args:
            field_name: Name of the field
            
        Returns:
            FieldRegion or None
        """
        for page_regions in self.field_regions.values():
            if field_name in page_regions:
                return page_regions[field_name]
        return None
    
    def align_form_to_template(
        self, 
        form_image: Image.Image, 
        page_number: int = 1
    ) -> Tuple[Image.Image, float, float]:
        """
        Align a filled form image to the template.
        
        Returns the aligned image and scale factors.
        
        Args:
            form_image: Filled form image
            page_number: Page number to align against
            
        Returns:
            Tuple of (aligned_image, scale_x, scale_y)
        """
        # If no template loaded or OpenCV not available, return original
        if not CV2_AVAILABLE or page_number not in self.template_images:
            # Calculate scale based on standard template size
            # Standard template is assumed to be 1700x2400
            scale_x = form_image.width / 1700
            scale_y = form_image.height / 2400
            return form_image, scale_x, scale_y
        
        try:
            template = self.template_images[page_number]
            
            # Convert to OpenCV format
            form_cv = np.array(form_image)
            template_cv = np.array(template)
            
            # Convert to grayscale
            if len(form_cv.shape) == 3:
                form_gray = cv2.cvtColor(form_cv, cv2.COLOR_RGB2GRAY)
            else:
                form_gray = form_cv
            
            if len(template_cv.shape) == 3:
                template_gray = cv2.cvtColor(template_cv, cv2.COLOR_RGB2GRAY)
            else:
                template_gray = template_cv
            
            # Detect features and match
            orb = cv2.ORB_create(nfeatures=500)
            kp1, des1 = orb.detectAndCompute(form_gray, None)
            kp2, des2 = orb.detectAndCompute(template_gray, None)
            
            if des1 is None or des2 is None:
                scale_x = form_image.width / template.width
                scale_y = form_image.height / template.height
                return form_image, scale_x, scale_y
            
            # Match features
            bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
            matches = bf.match(des1, des2)
            matches = sorted(matches, key=lambda x: x.distance)[:50]
            
            if len(matches) < 10:
                scale_x = form_image.width / template.width
                scale_y = form_image.height / template.height
                return form_image, scale_x, scale_y
            
            # Calculate homography
            src_pts = np.float32([kp1[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
            dst_pts = np.float32([kp2[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)
            
            M, _ = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
            
            if M is None:
                scale_x = form_image.width / template.width
                scale_y = form_image.height / template.height
                return form_image, scale_x, scale_y
            
            # Warp image to align with template
            h, w = template_gray.shape
            aligned = cv2.warpPerspective(form_cv, M, (w, h))
            
            return Image.fromarray(aligned), 1.0, 1.0
            
        except Exception as e:
            logger.warning(f"Template alignment failed: {e}")
            scale_x = form_image.width / 1700
            scale_y = form_image.height / 2400
            return form_image, scale_x, scale_y
    
    def extract_field_region(
        self, 
        image: Image.Image, 
        field_name: str,
        page_number: int = 1,
        padding: int = 5
    ) -> Optional[Image.Image]:
        """
        Extract a cropped image of a specific field region.
        
        Args:
            image: Form image
            field_name: Name of the field to extract
            page_number: Page number
            padding: Extra padding around the region
            
        Returns:
            Cropped image of the field or None
        """
        region = self.get_region_for_field(field_name)
        if not region:
            return None
        
        # Scale region to image size
        scale_x = image.width / 1700  # Assuming template is 1700px wide
        scale_y = image.height / 2400  # Assuming template is 2400px tall
        
        scaled_region = region.scale(scale_x, scale_y)
        
        # Add padding
        x1 = max(0, scaled_region.x - padding)
        y1 = max(0, scaled_region.y - padding)
        x2 = min(image.width, scaled_region.x + scaled_region.width + padding)
        y2 = min(image.height, scaled_region.y + scaled_region.height + padding)
        
        try:
            return image.crop((x1, y1, x2, y2))
        except Exception as e:
            logger.warning(f"Failed to extract field region {field_name}: {e}")
            return None
    
    def extract_all_field_regions(
        self, 
        image: Image.Image, 
        page_number: int = 1
    ) -> Dict[str, Image.Image]:
        """
        Extract cropped images for all fields on a page.
        
        Args:
            image: Form page image
            page_number: Page number
            
        Returns:
            Dictionary of field name to cropped image
        """
        regions = self.get_field_regions(page_number)
        result = {}
        
        for field_name in regions.keys():
            field_image = self.extract_field_region(image, field_name, page_number)
            if field_image:
                result[field_name] = field_image
        
        return result
    
    def get_field_type(self, field_name: str) -> Optional[str]:
        """
        Get the type of a field (text, checkbox, date, number).
        
        Args:
            field_name: Name of the field
            
        Returns:
            Field type string or None
        """
        region = self.get_region_for_field(field_name)
        return region.field_type if region else None


# Convenience functions
def get_field_region(field_name: str) -> Optional[FieldRegion]:
    """Get the template region for a field."""
    mapper = TemplateFieldMapper()
    return mapper.get_region_for_field(field_name)


def extract_field_from_image(
    image: Image.Image, 
    field_name: str, 
    page_number: int = 1
) -> Optional[Image.Image]:
    """Extract a field region from a form image."""
    mapper = TemplateFieldMapper()
    return mapper.extract_field_region(image, field_name, page_number)
