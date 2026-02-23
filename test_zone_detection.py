#!/usr/bin/env python3
"""
Test script for Zone Detection and Enhanced Preprocessing

Tests the new Phase 1 improvements:
1. Form Zone Detection
2. Image Preprocessing (deskew, line removal, text enhancement)
3. Zone-aware OCR extraction
"""

import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from PIL import Image


def test_zone_detector():
    """Test the FormZoneDetector class"""
    print("\n" + "="*60)
    print("Testing Form Zone Detector")
    print("="*60)
    
    try:
        from backend.utils.form_zone_detector import FormZoneDetector, detect_form_zones, get_zone_for_field
        
        detector = FormZoneDetector(form_type='srcc')
        
        # Test zone definitions
        print("\n✓ FormZoneDetector initialized successfully")
        
        # Check page 1 zones
        page1_zones = detector.zone_definitions.get('page_1', {})
        print(f"\n  Page 1 zones: {len(page1_zones)}")
        for zone_name in page1_zones.keys():
            print(f"    - {zone_name}")
        
        # Check page 2 zones
        page2_zones = detector.zone_definitions.get('page_2', {})
        print(f"\n  Page 2 zones: {len(page2_zones)}")
        for zone_name in page2_zones.keys():
            print(f"    - {zone_name}")
        
        # Test field-to-zone mapping
        print("\n  Field to zone mapping tests:")
        test_fields = ['student_name', 'email', 'mother_name', 'nationality', 'board_university']
        for field in test_fields:
            zone_info = get_zone_for_field(field)
            if zone_info:
                print(f"    {field} -> {zone_info['zone_name']} (page {zone_info['page']})")
            else:
                print(f"    {field} -> Not found")
        
        # Test reading order
        print("\n  Reading order for page 1:")
        reading_order = detector.get_reading_order(1)
        for i, zone in enumerate(reading_order, 1):
            print(f"    {i}. {zone}")
        
        print("\n✓ Zone detector tests passed!")
        return True
        
    except Exception as e:
        print(f"\n✗ Zone detector test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_image_preprocessing():
    """Test image preprocessing functions"""
    print("\n" + "="*60)
    print("Testing Image Preprocessing")
    print("="*60)
    
    try:
        from backend.utils.image_preprocessing import (
            deskew_image, remove_form_lines, enhance_handwriting,
            detect_text_regions, preprocess_for_form_ocr
        )
        
        print("\n✓ All preprocessing functions imported successfully")
        
        # Create a test image
        test_image = Image.new('RGB', (800, 1000), color='white')
        
        # Test deskew
        deskewed = deskew_image(test_image)
        print(f"  deskew_image: {deskewed.size}")
        
        # Test line removal
        no_lines = remove_form_lines(test_image)
        print(f"  remove_form_lines: {no_lines.size}")
        
        # Test handwriting enhancement
        enhanced = enhance_handwriting(test_image)
        print(f"  enhance_handwriting: {enhanced.size}")
        
        # Test text region detection
        regions = detect_text_regions(test_image)
        print(f"  detect_text_regions: {len(regions)} regions")
        
        # Test full pipeline
        processed = preprocess_for_form_ocr(test_image)
        print(f"  preprocess_for_form_ocr: {processed.size}")
        
        print("\n✓ Image preprocessing tests passed!")
        return True
        
    except Exception as e:
        print(f"\n✗ Image preprocessing test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_zone_aware_extraction():
    """Test zone-aware field extraction"""
    print("\n" + "="*60)
    print("Testing Zone-Aware Extraction")
    print("="*60)
    
    try:
        from backend.utils.srcc_form_extractor import (
            SRCCFormExtractor, extract_srcc_form, extract_srcc_form_with_zones
        )
        
        print("\n✓ SRCC Form Extractor imported successfully")
        
        # Test with sample text
        sample_text = """
        SHRI RAM COLLEGE OF COMMERCE
        STUDENT'S DATA FORM
        ACADEMIC SESSION 2024-2025
        
        Course: B.COM.(H)
        Admission Category: GEN
        
        DU Portal Form Number: 123456789012
        CUET Score: 851.147
        College Roll No.: 24BC123
        
        NAME IN BLOCK LETTERS
        1. ARYAN KUMAR
        First Name
        
        2. Gender: Male
        3. Date of Birth: 15/03/2006
        
        4. Permanent Address:
        123 Main Street, Delhi
        State: Delhi PIN: 110001
        
        6. Email: aryan.kumar@gmail.com
        7. Contact Numbers: 9876543210
        
        8. Mother's Name: SUNITA KUMAR
        9. Father's Name: RAJESH KUMAR
        """
        
        extractor = SRCCFormExtractor()
        
        # Test basic extraction
        result = extractor.extract(sample_text)
        print(f"\n  Basic extraction found {len(result)} fields:")
        for field, value in sorted(result.items()):
            if not field.startswith('_'):
                print(f"    {field}: {value}")
        
        # Test zone-aware extraction
        zone_hints = {
            'zones': {
                'student_name': {'fields': ['student_name'], 'extracted_fields': {}},
                'contact_details': {'fields': ['email', 'phone_number'], 'extracted_fields': {}},
            }
        }
        result_with_zones = extractor.extract(sample_text, zone_hints=zone_hints)
        print(f"\n  Zone-aware extraction found {len(result_with_zones)} fields")
        
        # Test confidence scoring
        if result.get('student_name'):
            confidence = extractor.get_field_confidence('student_name', result['student_name'], 'student_name')
            print(f"\n  Confidence for student_name: {confidence:.2f}")
        
        print("\n✓ Zone-aware extraction tests passed!")
        return True
        
    except Exception as e:
        print(f"\n✗ Zone-aware extraction test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_with_real_pdf():
    """Test with a real PDF from samples"""
    print("\n" + "="*60)
    print("Testing with Real PDF")
    print("="*60)
    
    try:
        from backend.utils.file_handler import load_all_pdf_pages
        from backend.utils.form_zone_detector import FormZoneDetector
        from backend.utils.image_preprocessing import preprocess_for_form_ocr
        
        # Find a sample PDF
        pdf_dir = Path(__file__).parent / "data" / "samples" / "pdfs"
        if not pdf_dir.exists():
            print(f"\n  Sample PDFs directory not found: {pdf_dir}")
            return True  # Not a failure, just no samples
        
        pdf_files = list(pdf_dir.glob("*.pdf"))
        if not pdf_files:
            print("\n  No PDF files found in samples")
            return True
        
        # Test with first PDF
        test_pdf = pdf_files[0]
        print(f"\n  Testing with: {test_pdf.name}")
        
        # Load pages
        pages = load_all_pdf_pages(str(test_pdf))
        print(f"  Loaded {len(pages)} pages")
        
        if pages:
            # Test zone detection on first page
            detector = FormZoneDetector(form_type='srcc')
            zones = detector.detect_zones(pages[0], page_number=1)
            print(f"  Detected {len(zones)} zones on page 1")
            
            # Test preprocessing
            processed = preprocess_for_form_ocr(pages[0])
            print(f"  Preprocessed image size: {processed.size}")
            
            # Extract zone images
            zone_images = detector.extract_zone_images(pages[0], page_number=1)
            print(f"  Extracted {len(zone_images)} zone images")
        
        print("\n✓ Real PDF test passed!")
        return True
        
    except Exception as e:
        print(f"\n✗ Real PDF test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("OCR Zone Detection & Preprocessing Tests")
    print("="*60)
    
    results = []
    
    # Run tests
    results.append(("Zone Detector", test_zone_detector()))
    results.append(("Image Preprocessing", test_image_preprocessing()))
    results.append(("Zone-Aware Extraction", test_zone_aware_extraction()))
    results.append(("Real PDF Processing", test_with_real_pdf()))
    
    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    
    passed = 0
    failed = 0
    for name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"  {status}: {name}")
        if success:
            passed += 1
        else:
            failed += 1
    
    print(f"\n  Total: {passed} passed, {failed} failed")
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
