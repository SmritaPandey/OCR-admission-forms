"""
Prepare Training Data from Student Admission Forms

This script converts verified student admission forms from your database
into the training format needed for CRAFT + TR-OCR training.

It extracts:
- Form images (from uploaded files)
- Ground truth text (from verified form fields)
- Creates JSON training data format
"""
import argparse
import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy.orm import Session
from backend.database import get_db, AdmissionForm, FormStatus
from backend.config import settings
from PIL import Image
import os


def extract_text_from_form(form: AdmissionForm) -> str:
    """
    Extract all text from a verified admission form.
    Combines all verified fields into a single text string.
    Includes ALL fields from the form images.
    """
    text_parts = []
    
    # Get additional_info for extra fields
    additional_info = form.additional_info if isinstance(form.additional_info, dict) else {}
    
    # Academic & Admission Details
    if additional_info.get('academic_session'):
        text_parts.append(f"Academic Session: {additional_info['academic_session']}")
    if additional_info.get('course'):
        text_parts.append(f"Course: {additional_info['course']}")
    if additional_info.get('admission_category'):
        text_parts.append(f"Admission Category: {additional_info['admission_category']}")
    if additional_info.get('du_portal_form_number'):
        text_parts.append(f"DU Portal Form Number: {additional_info['du_portal_form_number']}")
    if additional_info.get('cuet_score'):
        text_parts.append(f"CUET Score: {additional_info['cuet_score']}")
    if additional_info.get('college_roll_no'):
        text_parts.append(f"College Roll No.: {additional_info['college_roll_no']}")
    if additional_info.get('date_of_admission'):
        text_parts.append(f"Date of Admission: {additional_info['date_of_admission']}")
    
    # Name Fields
    if additional_info.get('first_name'):
        text_parts.append(f"First Name: {additional_info['first_name']}")
    if additional_info.get('middle_name'):
        text_parts.append(f"Middle Name: {additional_info['middle_name']}")
    if additional_info.get('surname'):
        text_parts.append(f"Surname: {additional_info['surname']}")
    if form.student_name:
        text_parts.append(f"Student Name: {form.student_name}")
    
    # Basic Details
    if form.date_of_birth:
        text_parts.append(f"Date of Birth: {form.date_of_birth}")
    if form.gender:
        text_parts.append(f"Gender: {form.gender}")
    if form.category:
        text_parts.append(f"Category: {form.category}")
    if form.nationality:
        text_parts.append(f"Nationality: {form.nationality}")
    if form.religion:
        text_parts.append(f"Religion: {form.religion}")
    if form.aadhar_number:
        text_parts.append(f"Aadhar Number: {form.aadhar_number}")
    if form.blood_group:
        text_parts.append(f"Blood Group: {form.blood_group}")
    if additional_info.get('below_poverty_line'):
        text_parts.append(f"Whether Below Poverty Line: {additional_info['below_poverty_line']}")
    if form.annual_income:
        text_parts.append(f"Annual Income: {form.annual_income}")
    if additional_info.get('minority_category'):
        text_parts.append(f"Minority Category: {additional_info['minority_category']}")
    
    # Address Details
    if additional_info.get('permanent_address_line1'):
        text_parts.append(f"Permanent Address Line 1: {additional_info['permanent_address_line1']}")
    if additional_info.get('permanent_address_line2'):
        text_parts.append(f"Permanent Address Line 2: {additional_info['permanent_address_line2']}")
    if additional_info.get('permanent_address_line3'):
        text_parts.append(f"Permanent Address Line 3: {additional_info['permanent_address_line3']}")
    if additional_info.get('permanent_state'):
        text_parts.append(f"Permanent State: {additional_info['permanent_state']}")
    if additional_info.get('permanent_pincode'):
        text_parts.append(f"Permanent PIN: {additional_info['permanent_pincode']}")
    if form.permanent_address:
        text_parts.append(f"Permanent Address: {form.permanent_address}")
    
    if additional_info.get('correspondence_address_line1'):
        text_parts.append(f"Correspondence Address Line 1: {additional_info['correspondence_address_line1']}")
    if additional_info.get('correspondence_address_line2'):
        text_parts.append(f"Correspondence Address Line 2: {additional_info['correspondence_address_line2']}")
    if additional_info.get('correspondence_address_line3'):
        text_parts.append(f"Correspondence Address Line 3: {additional_info['correspondence_address_line3']}")
    if additional_info.get('correspondence_state'):
        text_parts.append(f"Correspondence State: {additional_info['correspondence_state']}")
    if additional_info.get('correspondence_pincode'):
        text_parts.append(f"Correspondence PIN: {additional_info['correspondence_pincode']}")
    if form.correspondence_address:
        text_parts.append(f"Correspondence Address: {form.correspondence_address}")
    
    if form.city:
        text_parts.append(f"City: {form.city}")
    if form.state:
        text_parts.append(f"State: {form.state}")
    if form.pincode:
        text_parts.append(f"Pincode: {form.pincode}")
    
    # Contact Details
    if form.phone_number:
        text_parts.append(f"Phone: {form.phone_number}")
    if form.alternate_phone:
        text_parts.append(f"Alternate Phone: {form.alternate_phone}")
    if form.email:
        text_parts.append(f"Email: {form.email}")
    if form.emergency_contact_name:
        text_parts.append(f"Emergency Contact: {form.emergency_contact_name}")
    if form.emergency_contact_phone:
        text_parts.append(f"Emergency Contact Phone: {form.emergency_contact_phone}")
    
    # Parent/Guardian Details
    if form.father_name:
        text_parts.append(f"Father Name: {form.father_name}")
    if form.father_occupation:
        text_parts.append(f"Father Occupation: {form.father_occupation}")
    if additional_info.get('father_designation'):
        text_parts.append(f"Father Designation: {additional_info['father_designation']}")
    if additional_info.get('father_organization'):
        text_parts.append(f"Father Organization: {additional_info['father_organization']}")
    if additional_info.get('father_email'):
        text_parts.append(f"Father Email: {additional_info['father_email']}")
    if additional_info.get('father_mobile'):
        text_parts.append(f"Father Mobile: {additional_info['father_mobile']}")
    if additional_info.get('father_landline_code'):
        text_parts.append(f"Father Landline Code: {additional_info['father_landline_code']}")
    if additional_info.get('father_landline'):
        text_parts.append(f"Father Landline: {additional_info['father_landline']}")
    if form.father_phone:
        text_parts.append(f"Father Phone: {form.father_phone}")
    
    if form.mother_name:
        text_parts.append(f"Mother Name: {form.mother_name}")
    if form.mother_occupation:
        text_parts.append(f"Mother Occupation: {form.mother_occupation}")
    if additional_info.get('mother_designation'):
        text_parts.append(f"Mother Designation: {additional_info['mother_designation']}")
    if additional_info.get('mother_organization'):
        text_parts.append(f"Mother Organization: {additional_info['mother_organization']}")
    if additional_info.get('mother_email'):
        text_parts.append(f"Mother Email: {additional_info['mother_email']}")
    if additional_info.get('mother_mobile'):
        text_parts.append(f"Mother Mobile: {additional_info['mother_mobile']}")
    if additional_info.get('mother_landline_code'):
        text_parts.append(f"Mother Landline Code: {additional_info['mother_landline_code']}")
    if additional_info.get('mother_landline'):
        text_parts.append(f"Mother Landline: {additional_info['mother_landline']}")
    if form.mother_phone:
        text_parts.append(f"Mother Phone: {form.mother_phone}")
    
    if form.guardian_name:
        text_parts.append(f"Guardian Name: {form.guardian_name}")
    if form.guardian_relation:
        text_parts.append(f"Guardian Relation: {form.guardian_relation}")
    if additional_info.get('guardian_residential_address'):
        text_parts.append(f"Guardian Residential Address: {additional_info['guardian_residential_address']}")
    if additional_info.get('guardian_organization'):
        text_parts.append(f"Guardian Organization: {additional_info['guardian_organization']}")
    if additional_info.get('guardian_email'):
        text_parts.append(f"Guardian Email: {additional_info['guardian_email']}")
    if additional_info.get('guardian_mobile'):
        text_parts.append(f"Guardian Mobile: {additional_info['guardian_mobile']}")
    if additional_info.get('guardian_landline_code'):
        text_parts.append(f"Guardian Landline Code: {additional_info['guardian_landline_code']}")
    if additional_info.get('guardian_landline'):
        text_parts.append(f"Guardian Landline: {additional_info['guardian_landline']}")
    if form.guardian_phone:
        text_parts.append(f"Guardian Phone: {form.guardian_phone}")
    
    # Educational Qualifications
    if form.tenth_board:
        text_parts.append(f"10th Board: {form.tenth_board}")
    if form.tenth_year:
        text_parts.append(f"10th Year: {form.tenth_year}")
    if form.tenth_percentage:
        text_parts.append(f"10th Percentage: {form.tenth_percentage}")
    if form.tenth_school:
        text_parts.append(f"10th School: {form.tenth_school}")
    
    if form.twelfth_board:
        text_parts.append(f"12th Board: {form.twelfth_board}")
    if form.twelfth_year:
        text_parts.append(f"12th Year: {form.twelfth_year}")
    if additional_info.get('twelfth_roll_number'):
        text_parts.append(f"12th Roll Number: {additional_info['twelfth_roll_number']}")
    if additional_info.get('twelfth_institution'):
        text_parts.append(f"12th Institution: {additional_info['twelfth_institution']}")
    if additional_info.get('hindi_studied_upto'):
        text_parts.append(f"Hindi Studied Upto: {additional_info['hindi_studied_upto']}")
    if form.twelfth_percentage:
        text_parts.append(f"12th Percentage: {form.twelfth_percentage}")
    if form.twelfth_school:
        text_parts.append(f"12th School: {form.twelfth_school}")
    
    if form.previous_qualification:
        text_parts.append(f"Previous Qualification: {form.previous_qualification}")
    if form.graduation_details:
        text_parts.append(f"Graduation: {form.graduation_details}")
    
    # CUET Marks
    for i in range(1, 7):
        if additional_info.get(f'cuet_subject_{i}'):
            text_parts.append(f"CUET Subject {i}: {additional_info[f'cuet_subject_{i}']}")
        if additional_info.get(f'cuet_total_score_{i}'):
            text_parts.append(f"CUET Total Score {i}: {additional_info[f'cuet_total_score_{i}']}")
        if additional_info.get(f'cuet_score_obtained_{i}'):
            text_parts.append(f"CUET Score Obtained {i}: {additional_info[f'cuet_score_obtained_{i}']}")
    if additional_info.get('cuet_total_score'):
        text_parts.append(f"Total CUET Score: {additional_info['cuet_total_score']}")
    
    # Course Application Details
    if form.course_applied:
        text_parts.append(f"Course Applied: {form.course_applied}")
    if form.application_number:
        text_parts.append(f"Application Number: {form.application_number}")
    if form.enrollment_number:
        text_parts.append(f"Enrollment Number: {form.enrollment_number}")
    if form.admission_date:
        text_parts.append(f"Admission Date: {form.admission_date}")
    
    # Other Information
    if additional_info.get('du_enrollment_number'):
        text_parts.append(f"DU Enrollment Number: {additional_info['du_enrollment_number']}")
    if additional_info.get('hindi_medium_preference'):
        text_parts.append(f"Hindi Medium Preference: {additional_info['hindi_medium_preference']}")
    
    # Category Certificate Details
    if additional_info.get('category_certificate_authority'):
        text_parts.append(f"Certificate Authority: {additional_info['category_certificate_authority']}")
    if additional_info.get('category_certificate_number'):
        text_parts.append(f"Certificate Number: {additional_info['category_certificate_number']}")
    if additional_info.get('category_certificate_date'):
        text_parts.append(f"Certificate Date: {additional_info['category_certificate_date']}")
    if additional_info.get('disability_percentage'):
        text_parts.append(f"Disability Percentage: {additional_info['disability_percentage']}")
    if additional_info.get('disability_type'):
        text_parts.append(f"Disability Type: {additional_info['disability_type']}")
    if additional_info.get('udid_number'):
        text_parts.append(f"UDID Number: {additional_info['udid_number']}")
    
    # Also include raw OCR text if available
    if form.extracted_data and isinstance(form.extracted_data, dict):
        raw_text = form.extracted_data.get('raw_text', '')
        if raw_text:
            text_parts.append(f"\nRaw OCR Text:\n{raw_text}")
    
    return "\n".join(text_parts)


def prepare_training_data_from_database(
    db: Session,
    output_path: str,
    min_fields: int = 5,
    status: FormStatus = FormStatus.VERIFIED,
    limit: Optional[int] = None
) -> Dict[str, Any]:
    """
    Prepare training data from verified student admission forms in database.
    
    Args:
        db: Database session
        output_path: Path to save training JSON file
        min_fields: Minimum number of verified fields required
        status: Form status to include (default: VERIFIED)
        limit: Maximum number of forms to include (None = all)
    
    Returns:
        Dictionary with statistics about prepared data
    """
    print("=" * 80)
    print("Preparing Training Data from Student Admission Forms")
    print("=" * 80)
    print()
    
    # Query verified forms
    query = db.query(AdmissionForm).filter(AdmissionForm.status == status)
    
    if limit:
        query = query.limit(limit)
    
    forms = query.order_by(AdmissionForm.verified_date.desc()).all()
    
    print(f"Found {len(forms)} {status.value} forms in database")
    print()
    
    training_data = []
    skipped = 0
    stats = {
        "total_forms": len(forms),
        "processed": 0,
        "skipped": 0,
        "missing_files": 0,
        "insufficient_fields": 0
    }
    
    for form in forms:
        # Check if file exists
        file_path = Path(form.file_path)
        if not file_path.exists():
            print(f"⚠️  Skipping form {form.id}: File not found: {form.file_path}")
            stats["missing_files"] += 1
            skipped += 1
            continue
        
        # Extract text from verified fields
        text = extract_text_from_form(form)
        
        # Count non-empty fields
        field_count = len([line for line in text.split('\n') if line.strip() and ':' in line])
        
        if field_count < min_fields:
            print(f"⚠️  Skipping form {form.id}: Only {field_count} fields (minimum: {min_fields})")
            stats["insufficient_fields"] += 1
            skipped += 1
            continue
        
        # Verify image can be loaded
        try:
            if file_path.suffix.lower() == '.pdf':
                # For PDFs, we'll use the first page
                from pdf2image import convert_from_path
                images = convert_from_path(str(file_path), first_page=1, last_page=1)
                if not images:
                    raise ValueError("Could not extract image from PDF")
                # Save first page as image for training
                image_output = Path(settings.UPLOAD_DIR) / "training_images" / f"form_{form.id}_page1.png"
                image_output.parent.mkdir(parents=True, exist_ok=True)
                images[0].save(image_output)
                image_path = str(image_output)
            else:
                # For images, verify it can be opened
                img = Image.open(file_path)
                img.verify()
                image_path = str(file_path)
        except Exception as e:
            print(f"⚠️  Skipping form {form.id}: Error loading image: {e}")
            stats["missing_files"] += 1
            skipped += 1
            continue
        
        # Add to training data
        training_data.append({
            "image_path": image_path,
            "text": text.strip(),
            "form_id": form.id,
            "student_name": form.student_name,
            "field_count": field_count,
            "verified_date": form.verified_date.isoformat() if form.verified_date else None
        })
        
        stats["processed"] += 1
        if stats["processed"] % 10 == 0:
            print(f"✅ Processed {stats['processed']} forms...")
    
    stats["skipped"] = skipped
    
    # Save training data
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(training_data, f, indent=2, ensure_ascii=False)
    
    print()
    print("=" * 80)
    print("Training Data Preparation Complete")
    print("=" * 80)
    print(f"✅ Processed: {stats['processed']} forms")
    print(f"⚠️  Skipped: {stats['skipped']} forms")
    print(f"   - Missing files: {stats['missing_files']}")
    print(f"   - Insufficient fields: {stats['insufficient_fields']}")
    print()
    print(f"📁 Training data saved to: {output_file}")
    print(f"   Total samples: {len(training_data)}")
    print()
    
    if len(training_data) == 0:
        print("❌ No training data generated!")
        print("   Make sure you have verified forms in the database.")
        print("   Forms need at least 5 verified fields to be included.")
    else:
        print("✅ Ready for training!")
        print()
        print("Next step: Train the model")
        print(f"  python backend/training/train_craft_trocr.py {output_file} models/trocr_student_forms")
    
    return {
        **stats,
        "output_file": str(output_file),
        "samples": len(training_data)
    }


def main():
    """CLI interface"""
    parser = argparse.ArgumentParser(
        description="Prepare training data from verified student admission forms",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "output",
        help="Output JSON file path for training data"
    )
    parser.add_argument(
        "--min-fields",
        type=int,
        default=5,
        help="Minimum number of verified fields required"
    )
    parser.add_argument(
        "--status",
        type=str,
        default="verified",
        choices=["uploaded", "extracted", "verified", "error"],
        help="Form status to include"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of forms to include (None = all)"
    )
    parser.add_argument(
        "--database-url",
        help="Database URL (default: from config)"
    )
    
    args = parser.parse_args()
    
    # Get database session
    if args.database_url:
        from backend.config import settings
        settings.DATABASE_URL = args.database_url
    
    # Convert status string to enum
    status_map = {
        "uploaded": FormStatus.UPLOADED,
        "extracted": FormStatus.EXTRACTED,
        "verified": FormStatus.VERIFIED,
        "error": FormStatus.ERROR
    }
    status = status_map[args.status.lower()]
    
    # Get database session
    db = next(get_db())
    
    try:
        result = prepare_training_data_from_database(
            db=db,
            output_path=args.output,
            min_fields=args.min_fields,
            status=status,
            limit=args.limit
        )
        
        if result["samples"] == 0:
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()

