import logging

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from backend.database import get_db, AdmissionForm, FormStatus, StudentDocument
from backend.models.form import (
    FormDetailResponse,
    FormVerification,
    FormSearchParams,
    FormExtractionResponse,
    ExtractedData,
)
from backend.api.routes.students import get_or_create_student_profile
from backend.ocr import get_ocr_provider
from backend.utils.file_handler import load_image
from backend.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


def apply_form_filters(
    query,
    *,
    student_name: Optional[str] = None,
    phone_number: Optional[str] = None,
    email: Optional[str] = None,
    enrollment_number: Optional[str] = None,
    application_number: Optional[str] = None,
    course_applied: Optional[str] = None,
    status: Optional[FormStatus] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) :
    """Apply common filters to the admission forms query."""
    if student_name:
        query = query.filter(AdmissionForm.student_name.ilike(f"%{student_name.strip()}%"))
    if phone_number:
        query = query.filter(AdmissionForm.phone_number.ilike(f"%{phone_number.strip()}%"))
    if email:
        query = query.filter(AdmissionForm.email.ilike(f"%{email.strip()}%"))
    if enrollment_number:
        query = query.filter(AdmissionForm.enrollment_number.ilike(f"%{enrollment_number.strip()}%"))
    if application_number:
        query = query.filter(AdmissionForm.application_number.ilike(f"%{application_number.strip()}%"))
    if course_applied:
        query = query.filter(AdmissionForm.course_applied.ilike(f"%{course_applied.strip()}%"))
    if status:
        query = query.filter(AdmissionForm.status == status)

    if date_from:
        start = date_from.replace(hour=0, minute=0, second=0, microsecond=0)
        query = query.filter(AdmissionForm.upload_date >= start)
    if date_to:
        end = date_to.replace(hour=23, minute=59, second=59, microsecond=999999)
        query = query.filter(AdmissionForm.upload_date <= end)

    return query

@router.get("/", response_model=List[FormDetailResponse])
async def list_forms(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=1000),
    status: Optional[FormStatus] = None,
    db: Session = Depends(get_db)
):
    """List all admission forms with pagination"""
    query = db.query(AdmissionForm)
    
    if status:
        query = query.filter(AdmissionForm.status == status)
    
    forms = query.order_by(AdmissionForm.upload_date.desc()).offset(skip).limit(limit).all()
    
    # Include documents for each form
    from backend.models.document import DocumentResponse
    result = []
    for form in forms:
        form_data = FormDetailResponse.model_validate(form)
        documents = db.query(StudentDocument).filter(
            StudentDocument.form_id == form.id
        ).all()
        form_data.documents = [DocumentResponse.model_validate(doc) for doc in documents]
        result.append(form_data)
    
    return result

@router.get("/{form_id}", response_model=FormDetailResponse)
async def get_form(form_id: int, db: Session = Depends(get_db)):
    """Get detailed information about a specific form"""
    form = db.query(AdmissionForm).filter(AdmissionForm.id == form_id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    
    # Get associated documents
    documents = db.query(StudentDocument).filter(
        StudentDocument.form_id == form_id
    ).order_by(StudentDocument.upload_date.desc()).all()
    
    from backend.models.document import DocumentResponse
    form_data = FormDetailResponse.model_validate(form)
    form_data.documents = [DocumentResponse.model_validate(doc) for doc in documents]
    
    return form_data

@router.post(
    "/{form_id}/extract",
    response_model=FormExtractionResponse,
    summary="Re-extract a form using the selected OCR provider",
)
async def re_extract_form(
    form_id: int,
    ocr_provider: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Re-extract text from a form using a different or same OCR provider"""
    form = db.query(AdmissionForm).filter(AdmissionForm.id == form_id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    
    try:
        provider_name = (ocr_provider or form.ocr_provider or settings.OCR_PROVIDER).lower()
        if provider_name == "multi":
            provider_name = "best"

        provider = None
        multi_ocr = None
        if provider_name == "best":
            from backend.ocr.multi_provider import MultiProviderOCR
            multi_ocr = MultiProviderOCR()
        else:
            try:
                provider = get_ocr_provider(provider_name)
            except ValueError as e:
                # Provider not available - return helpful error message
                raise HTTPException(
                    status_code=400,
                    detail=f"OCR provider '{provider_name}' is not available. {str(e)}. Please select a different provider or configure this one in your settings."
                )

        selected_provider = provider_name

        # Construct full path from relative path
        import os
        from pathlib import Path
        from backend.utils.file_handler import load_all_pdf_pages, get_file_extension
        upload_dir = Path(settings.UPLOAD_DIR).resolve()
        full_file_path = upload_dir / form.file_path
        
        # Check if file exists
        if not full_file_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Form file not found: {form.file_path}. The file may have been moved or deleted."
            )
        
        # Check if it's a PDF - process all pages
        file_ext = get_file_extension(str(full_file_path))
        is_pdf = file_ext == 'pdf'
        
        if is_pdf:
            # Load all pages from PDF
            pages = load_all_pdf_pages(str(full_file_path))
            
            # Process each page with OCR and combine results
            all_raw_text = []
            all_confidences = []
            page_results = []
            
            for page_index, page_image in enumerate(pages, start=1):
                try:
                    # Use enhanced OCR extraction with preprocessing for Tesseract
                    if provider_name == "best":
                        page_result = await multi_ocr.extract_with_best_provider(page_image)
                        if page_index == 1:
                            selected_provider = page_result.get('provider_used', 'multi')
                    elif provider_name == "tesseract":
                        page_result = await provider.extract_text(page_image, preprocess=True)
                    else:
                        page_result = await provider.extract_text(page_image)
                    
                    # Collect text and confidence from each page
                    if page_result.get('raw_text'):
                        all_raw_text.append(f"\n--- Page {page_index} ---\n{page_result['raw_text']}")
                        if page_result.get('confidence'):
                            all_confidences.append(page_result['confidence'])
                    
                    page_results.append({
                        'page': page_index,
                        'raw_text': page_result.get('raw_text', ''),
                        'confidence': page_result.get('confidence', 0.0),
                        'provider': page_result.get('provider_used', selected_provider)
                    })
                    
                except Exception as page_error:
                    # Continue with other pages if one fails
                    print(f"Error processing page {page_index}: {str(page_error)}")
                    continue
            
            # Combine all pages' text
            combined_text = "\n".join(all_raw_text)
            avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0
            
            ocr_result: Dict[str, Any] = {
                "raw_text": combined_text,
                "confidence": round(avg_confidence, 2),
                "structured_data": None,
                "provider": selected_provider,
                "pages_processed": len(pages),
                "page_results": page_results
            }
        else:
            # Single image file - process normally
            image = load_image(str(full_file_path))
            
            # Use enhanced OCR extraction with preprocessing for Tesseract
            if provider_name == "best":
                ocr_result = await multi_ocr.extract_with_best_provider(image)
                selected_provider = ocr_result.get('provider_used', 'multi')
            elif provider_name == "tesseract":
                ocr_result = await provider.extract_text(image, preprocess=True)
            else:
                ocr_result = await provider.extract_text(image)
            ocr_result.setdefault("pages_processed", 1)
            ocr_result.setdefault(
                "page_results",
                [
                    {
                        "page": 1,
                        "raw_text": ocr_result.get("raw_text", ""),
                        "confidence": ocr_result.get("confidence"),
                        "provider": ocr_result.get("provider", selected_provider),
                    }
                ],
            )
            ocr_result.setdefault("provider", selected_provider)
        
        # Parse structured data from OCR text - ALWAYS parse (not just SRCC forms)
        if ocr_result.get('raw_text'):
            from backend.utils.form_parser import parse_form_text
            from backend.utils.ai_form_parser import AIFormParser
            
            # First, use AI form parser for initial extraction
            ai_parser = AIFormParser()
            structured_data = {}
            
            if ocr_result.get('structured_data'):
                ai_parsed = ai_parser.parse_from_ai_result(ocr_result)
                structured_data.update(ai_parsed)
            
            # Parse from raw text as well
            text_parsed = ai_parser.parse_from_text(ocr_result['raw_text'])
            structured_data.update(text_parsed)
            
            # NOW use SRCC form parser - its results take precedence
            # This parser is specifically designed for SRCC form layout
            srcc_parsed = parse_form_text(ocr_result['raw_text'])
            
            # Only use SRCC values if they look valid (not garbage)
            for field, value in srcc_parsed.items():
                if value and len(str(value)) > 1:
                    # Check if value is not garbage (common pattern check)
                    value_str = str(value)
                    if not any(garbage in value_str.lower() for garbage in [
                        'please', 'tick', 'check', 'enter', 'fill', 'select',
                        'details', 'information', 'particulars', 'mandatory'
                    ]):
                        structured_data[field] = value
            
            # Post-processing: Clean up garbage values from AI parser
            # These fields often have incorrect values from AI parsing
            def validate_name(v):
                if not v:
                    return None
                v = str(v).strip()
                # Names shouldn't be too long (likely garbage) or contain repeated patterns
                if len(v) > 50:
                    return None
                # Check for repeated words (garbage pattern)
                words = v.lower().split()
                if len(words) > 3 and len(set(words)) < len(words) / 2:
                    return None
                # Check for common garbage patterns
                garbage_patterns = ['central board', 'secondary education', 'education central', 'board secondary']
                if any(g in v.lower() for g in garbage_patterns):
                    return None
                return v
            
            def validate_enrollment(v):
                if not v:
                    return None
                v = str(v).strip()
                # Must be alphanumeric with at least one letter and one digit
                if v.upper() in ['DATE', 'NO', 'NUMBER', 'CARL', 'NAME']:
                    return None
                if len(v) < 4 or len(v) > 15:
                    return None
                # Valid SRCC roll format: digit(s) + letters + digits (like 24BC156 or 2YBC102)
                import re
                if re.match(r'^\d+[A-Z]+\d+$', v.upper()):
                    return v
                # Pure year like "2017" is not an enrollment number
                if v.isdigit() and len(v) == 4:
                    return None
                return v
            
            garbage_cleanup = {
                # Annual income can be numeric OR text like "BELOW 2 LAKHS"
                'annual_income': lambda v: v if v and (str(v).replace(',', '').isdigit() or 'LAKH' in str(v).upper() or 'BELOW' in str(v).upper()) else None,
                'blood_group': lambda v: v if v and v.upper().replace(' ', '') in ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'] else None,
                'nationality': lambda v: v if v and v.upper() in ['INDIAN', 'NEPALESE', 'BHUTANESE', 'TIBETAN'] else None,
                'religion': lambda v: v if v and v.upper() in ['HINDU', 'MUSLIM', 'SIKH', 'CHRISTIAN', 'JAIN', 'BUDDHIST', 'PARSI'] else None,
                'state': lambda v: v if v and len(v) > 1 and v.upper() not in ['OF', 'DOMICILE', 'NA', 'STATE'] else None,
                'course_applied': lambda v: v if v and ('B.COM' in v.upper() or 'B.A' in v.upper() or 'COMMERCE' in v.upper() or 'ECONOMICS' in v.upper()) else None,
                'aadhar_number': lambda v: v if v and len(str(v).replace(' ', '')) == 12 and str(v).replace(' ', '').isdigit() else None,
                'graduation_details': lambda v: v if v and 'honours' not in v.lower() and len(v) > 5 else None,
                'enrollment_number': validate_enrollment,
                'father_name': validate_name,
                'mother_name': validate_name,
                'guardian_name': validate_name,
            }
            
            for field, validator in garbage_cleanup.items():
                if field in structured_data:
                    cleaned = validator(structured_data[field])
                    if cleaned is None:
                        del structured_data[field]
                    else:
                        structured_data[field] = cleaned
            
            # Improve confidence score based on extracted field validation
            try:
                from backend.utils.confidence_scorer import improve_ocr_confidence
                original_confidence = ocr_result.get('confidence', 0)
                improved_confidence = improve_ocr_confidence(
                    structured_data,
                    original_confidence
                )
                ocr_result['confidence'] = round(improved_confidence, 2)
                ocr_result['confidence_improved'] = True
                ocr_result['original_confidence'] = original_confidence
            except Exception:
                # If confidence scorer fails, use original confidence
                pass
            
            # Store structured data
            ocr_result['structured_data'] = structured_data
            
            # Fields that should always be cleaned if invalid
            # (clear old garbage values)
            garbage_prone_fields = ['annual_income', 'blood_group', 'nationality', 'religion', 
                                    'state', 'course_applied', 'graduation_details', 'aadhar_number',
                                    'enrollment_number']
            for field in garbage_prone_fields:
                if field not in structured_data:
                    # Clear old garbage value
                    setattr(form, field, None)
            
            # Auto-fill all form fields if available
            for field in [
                # Basic identification
                'student_name', 'first_name', 'middle_name', 'surname',
                'date_of_birth', 'gender', 'category', 'nationality', 'religion',
                'aadhar_number', 'blood_group', 'below_poverty_line', 'minority_category',
                # Address
                'permanent_address', 'permanent_state', 'permanent_pincode',
                'correspondence_address', 'correspondence_state', 'correspondence_pincode',
                'pincode', 'city', 'state',
                # Contact
                'phone_number', 'alternate_phone', 'email',
                'emergency_contact_name', 'emergency_contact_phone',
                # Parents/Guardian
                'father_name', 'father_occupation', 'father_phone', 'father_email', 'father_mobile',
                'mother_name', 'mother_occupation', 'mother_phone', 'mother_email', 'mother_mobile',
                'guardian_name', 'guardian_relation', 'guardian_phone', 'guardian_mobile',
                # Academic/Admission
                'academic_session', 'course', 'cuet_score', 'college_roll_no', 'date_of_admission',
                'du_portal_form_number', 'admission_category',
                # Income
                'annual_income',
                # Education
                'tenth_board', 'tenth_year', 'tenth_percentage', 'tenth_school',
                'twelfth_board', 'twelfth_year', 'twelfth_percentage', 'twelfth_school',
                'twelfth_roll_number', 'twelfth_institution', 'hindi_studied_upto',
                'previous_qualification', 'graduation_details',
                # Other
                'du_enrollment_number', 'hindi_medium_preference',
                'course_applied', 'application_number', 'enrollment_number',
                'admission_date', 'exam_roll_no'
            ]:
                if structured_data.get(field):
                    setattr(form, field, structured_data[field])
        
        # Check if form is empty (template)
        from backend.utils.empty_form_detector import EmptyFormDetector
        empty_detector = EmptyFormDetector()
        empty_check = empty_detector.detect_empty(ocr_result)
        
        # Add empty form detection to extracted_data
        ocr_result['empty_form_detection'] = empty_check
        
        form.extracted_data = ocr_result
        form.ocr_provider = selected_provider
        form.status = FormStatus.EXTRACTED
        
        # Add warning to additional_info if empty
        if empty_check.get('is_empty') and empty_check.get('confidence', 0) > 0.7:
            if form.additional_info is None:
                form.additional_info = {}
            form.additional_info['empty_form_warning'] = {
                'message': empty_detector.get_empty_form_message(),
                'detection': empty_check
            }
        
        db.commit()

        logger.info(
            "Re-extracted form %s with provider %s (pages=%s, confidence=%s)",
            form_id,
            selected_provider,
            ocr_result.get("pages_processed"),
            ocr_result.get("confidence"),
        )
        
        return FormExtractionResponse(
            message="Re-extraction completed",
            result=ExtractedData(**ocr_result),
        )
        
    except Exception as e:
        form.status = FormStatus.ERROR
        db.commit()
        logger.exception(
            "Re-extraction failed for form %s with provider %s", form_id, provider_name
        )
        raise HTTPException(status_code=500, detail=f"Re-extraction failed: {str(e)}")

@router.put("/{form_id}/verify", response_model=FormDetailResponse)
async def verify_form(
    form_id: int,
    verification: FormVerification,
    db: Session = Depends(get_db)
):
    """Save verified/corrected student information"""
    form = db.query(AdmissionForm).filter(AdmissionForm.id == form_id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    
    # Update form with ALL verified data fields
    all_fields = [
        # Basic Personal Details
        'student_name', 'first_name', 'middle_name', 'surname',
        'date_of_birth', 'gender', 'category', 'nationality', 'religion',
        'aadhar_number', 'blood_group', 'below_poverty_line', 'minority_category',
        
        # Academic & Admission Details
        'academic_session', 'course', 'admission_category', 'admission_category_other',
        'du_portal_form_number', 'cuet_score', 'college_roll_no', 'date_of_admission',
        'course_applied', 'application_number', 'enrollment_number', 'admission_date',
        'du_enrollment_number', 'hindi_medium_preference',
        
        # Address Details
        'permanent_address', 'permanent_address_line1', 'permanent_address_line2', 
        'permanent_address_line3', 'permanent_state', 'permanent_pincode',
        'correspondence_address', 'correspondence_address_line1', 'correspondence_address_line2',
        'correspondence_address_line3', 'correspondence_state', 'correspondence_pincode',
        'pincode', 'city', 'state',
        
        # Contact Details
        'phone_number', 'alternate_phone', 'email', 
        'emergency_contact_name', 'emergency_contact_phone',
        
        # Mother's Details
        'mother_name', 'mother_occupation', 'mother_designation', 'mother_organization',
        'mother_email', 'mother_mobile', 'mother_landline_code', 'mother_landline', 'mother_phone',
        
        # Father's Details
        'father_name', 'father_occupation', 'father_designation', 'father_organization',
        'father_email', 'father_mobile', 'father_landline_code', 'father_landline', 'father_phone',
        
        # Guardian Details
        'guardian_name', 'guardian_relation', 'guardian_residential_address', 'guardian_organization',
        'guardian_email', 'guardian_mobile', 'guardian_landline_code', 'guardian_landline', 'guardian_phone',
        
        # Family Income
        'annual_income',
        
        # Academic History
        'tenth_board', 'tenth_year', 'tenth_percentage', 'tenth_school',
        'twelfth_board', 'twelfth_year', 'twelfth_percentage', 'twelfth_school',
        'twelfth_roll_number', 'twelfth_institution', 'hindi_studied_upto',
        'previous_qualification', 'graduation_details',
        
        # Certificate Details
        'category_certificate_authority', 'category_certificate_number', 'category_certificate_date',
        'disability_percentage', 'disability_type', 'udid_number',
        
        # CUET Marks
        'cuet_subject_1', 'cuet_total_score_1', 'cuet_score_obtained_1',
        'cuet_subject_2', 'cuet_total_score_2', 'cuet_score_obtained_2',
        'cuet_subject_3', 'cuet_total_score_3', 'cuet_score_obtained_3',
        'cuet_subject_4', 'cuet_total_score_4', 'cuet_score_obtained_4',
        'cuet_subject_5', 'cuet_total_score_5', 'cuet_score_obtained_5',
        'cuet_subject_6', 'cuet_total_score_6', 'cuet_score_obtained_6',
        'cuet_total_score',
        
        # Document Checklist
        'doc_admission_form', 'doc_undertaking_ragging', 'doc_photographs',
        'doc_cuet_scorecard', 'doc_class_xii_marksheet', 'doc_class_x_certificate',
        'doc_class_xii_certificate', 'doc_character_certificate', 'doc_transfer_certificate',
        'doc_hindi_certificate', 'doc_caste_certificate', 'doc_sports_eca',
        'doc_originals', 'doc_photo_id',
    ]
    
    for field in all_fields:
        value = getattr(verification, field, None)
        if value is not None and hasattr(form, field):
            setattr(form, field, value)
    
    # Sync category and admission_category (they are the same field)
    if form.admission_category and not form.category:
        form.category = form.admission_category
    elif form.category and not form.admission_category:
        form.admission_category = form.category
    elif form.admission_category:
        form.category = form.admission_category

    form.additional_info = verification.additional_info or {}

    # Validate required field: student_name
    if not verification.student_name or not verification.student_name.strip():
        raise HTTPException(
            status_code=400,
            detail="Student name is required. A form cannot be verified without a student name."
        )
    
    # Only mark as verified if student_name is provided
    form.status = FormStatus.VERIFIED
    form.verified_date = datetime.utcnow()
    
    # Auto-link to student profile if student_name is provided
    if verification.student_name:
        try:
            profile = get_or_create_student_profile(
                db,
                verification.student_name,
                verification.aadhar_number
            )
            form.student_profile_id = profile.id
        except Exception as e:
            # Log error but don't fail the verification
            logger.warning(f"Could not link form to student profile: {e}")
        
        # Rename file to include student name (only if not already renamed)
        try:
            from backend.utils.file_handler import rename_form_file, sanitize_filename
            
            # Check if filename already contains student name (avoid renaming multiple times)
            sanitized_name = sanitize_filename(verification.student_name).lower()
            current_filename_lower = form.filename.lower()
            
            # Only rename if filename doesn't already start with the student name pattern
            # Check if filename starts with sanitized name followed by underscore and form_id
            expected_prefix = f"{sanitized_name}_{form.id}".lower()
            
            if sanitized_name and not current_filename_lower.startswith(expected_prefix):
                new_file_path, new_filename = rename_form_file(
                    form.file_path,
                    verification.student_name,
                    form.id
                )
                form.file_path = new_file_path
                form.filename = new_filename
                logger.info(f"Renamed form {form.id} file to: {new_filename}")
        except Exception as e:
            # Log error but don't fail the verification
            logger.warning(f"Could not rename form file: {e}")
    
    # Track corrections for continuous improvement
    try:
        from backend.utils.continuous_improvement import ContinuousImprovementManager
        
        improvement_manager = ContinuousImprovementManager()
        
        # Compare verified values with original extracted values to find corrections
        extracted_data = form.extracted_data or {}
        structured_data = extracted_data.get('structured_data', {})
        
        # Track corrections for each field
        for field_name in ['student_name', 'date_of_birth', 'gender', 'category', 
                          'nationality', 'religion', 'aadhar_number', 'blood_group',
                          'permanent_address', 'correspondence_address', 'pincode', 
                          'city', 'state', 'phone_number', 'alternate_phone', 'email',
                          'emergency_contact_name', 'emergency_contact_phone',
                          'father_name', 'father_occupation', 'father_phone',
                          'mother_name', 'mother_occupation', 'mother_phone',
                          'guardian_name', 'guardian_relation', 'guardian_phone',
                          'annual_income', 'tenth_board', 'tenth_year', 'tenth_percentage',
                          'tenth_school', 'twelfth_board', 'twelfth_year', 
                          'twelfth_percentage', 'twelfth_school', 'previous_qualification',
                          'graduation_details', 'course_applied', 'application_number',
                          'enrollment_number', 'admission_date']:
            
            verified_value = getattr(verification, field_name, None)
            original_value = structured_data.get(field_name) or getattr(form, field_name, None)
            
            # Record correction if values differ
            if verified_value and original_value and str(verified_value).strip() != str(original_value).strip():
                confidence = extracted_data.get('confidence', 0) / 100.0 if extracted_data.get('confidence') else None
                improvement_manager.record_correction(
                    form_id=form_id,
                    field_name=field_name,
                    original_value=str(original_value),
                    corrected_value=str(verified_value),
                    confidence=confidence
                )
    except Exception as e:
        # Log but don't fail verification if improvement tracking fails
        logger.warning(f"Failed to track corrections for continuous improvement: {e}")
    
    # Train Google OCR with verified corrections
    try:
        from backend.training.train_google_ocr import GoogleOCRTrainer
        
        trainer = GoogleOCRTrainer()
        
        # Get raw OCR text from extracted data
        extracted_data = form.extracted_data or {}
        raw_text = extracted_data.get('raw_text', '')
        
        if raw_text:
            # Get extracted fields (before verification)
            extracted_fields = {}
            structured_data = extracted_data.get('structured_data', {})
            for key, value in structured_data.items():
                if isinstance(value, str) and value:
                    extracted_fields[key] = value
            
            # Get verified fields (after verification)
            verified_fields = {}
            for field_name in ['student_name', 'date_of_birth', 'gender', 'category',
                              'nationality', 'religion', 'aadhar_number', 'blood_group',
                              'permanent_address', 'correspondence_address', 'pincode',
                              'phone_number', 'email', 'father_name', 'mother_name',
                              'course_applied', 'application_number', 'enrollment_number']:
                value = getattr(verification, field_name, None)
                if value:
                    verified_fields[field_name] = str(value)
            
            if verified_fields:
                # Add to training data
                result = trainer.add_verified_sample(
                    form_id=str(form_id),
                    raw_ocr_text=raw_text,
                    extracted_fields=extracted_fields,
                    verified_fields=verified_fields,
                    image_path=form.file_path
                )
                logger.info(f"Added form {form_id} to Google OCR training: accuracy={result.get('accuracy', 0):.2f}")
    except Exception as e:
        logger.warning(f"Failed to add form to Google OCR training: {e}")
    
    # Automatically create annotation from verified data for training
    try:
        from backend.api.routes.annotation import AnnotationField, AnnotationCheckbox
        
        annotation_fields = []
        # Create annotation fields from verified data
        field_mapping = {
            'student_name': 'student_name',
            'date_of_birth': 'date_of_birth',
            'gender': 'gender',
            'category': 'category',
            'nationality': 'nationality',
            'religion': 'religion',
            'aadhar_number': 'aadhar_number',
            'blood_group': 'blood_group',
            'permanent_address': 'permanent_address',
            'correspondence_address': 'correspondence_address',
            'pincode': 'pincode',
            'city': 'city',
            'state': 'state',
            'phone_number': 'phone_number',
            'alternate_phone': 'alternate_phone',
            'email': 'email',
            'emergency_contact_name': 'emergency_contact_name',
            'emergency_contact_phone': 'emergency_contact_phone',
            'father_name': 'father_name',
            'father_occupation': 'father_occupation',
            'father_phone': 'father_phone',
            'mother_name': 'mother_name',
            'mother_occupation': 'mother_occupation',
            'mother_phone': 'mother_phone',
            'guardian_name': 'guardian_name',
            'guardian_relation': 'guardian_relation',
            'guardian_phone': 'guardian_phone',
            'annual_income': 'annual_income',
            'tenth_board': 'tenth_board',
            'tenth_year': 'tenth_year',
            'tenth_percentage': 'tenth_percentage',
            'tenth_school': 'tenth_school',
            'twelfth_board': 'twelfth_board',
            'twelfth_year': 'twelfth_year',
            'twelfth_percentage': 'twelfth_percentage',
            'twelfth_school': 'twelfth_school',
            'previous_qualification': 'previous_qualification',
            'graduation_details': 'graduation_details',
            'course_applied': 'course_applied',
            'application_number': 'application_number',
            'enrollment_number': 'enrollment_number',
            'admission_date': 'admission_date',
        }
        
        for field_key, field_name in field_mapping.items():
            value = getattr(verification, field_key, None)
            if value and str(value).strip():
                annotation_fields.append(AnnotationField(
                    field_name=field_name,
                    value=str(value).strip(),
                    page_number=1,
                    confidence=1.0  # Verified data has 100% confidence
                ))
        
        # Create key-value pairs for training
        key_value_pairs = {f.field_name: f.value for f in annotation_fields}
        
        # Store annotation in additional_info
        form.additional_info['annotation'] = {
            'fields': [f.dict() for f in annotation_fields],
            'checkboxes': [],
            'key_value_pairs': key_value_pairs,
            'notes': 'Auto-created from verified form data',
            'annotated_at': datetime.utcnow().isoformat(),
            'annotated_by': 'verification-api'
        }
        
        logger.info(f"Created annotation for form {form_id} with {len(annotation_fields)} fields")
    except Exception as e:
        # Log error but don't fail verification
        logger.warning(f"Failed to create annotation for form {form_id}: {e}")
    
    db.commit()
    db.refresh(form)
    
    # Get associated documents
    documents = db.query(StudentDocument).filter(
        StudentDocument.form_id == form.id
    ).order_by(StudentDocument.upload_date.desc()).all()
    
    from backend.models.document import DocumentResponse
    form_data = FormDetailResponse.model_validate(form)
    form_data.documents = [DocumentResponse.model_validate(doc) for doc in documents]
    
    return form_data

@router.put("/{form_id}", response_model=FormDetailResponse)
async def update_form(
    form_id: int,
    verification: FormVerification,
    verify: bool = Query(False, description="If True, mark form as verified and link to student profile"),
    db: Session = Depends(get_db)
):
    """Update form data. Use verify=True to mark as verified and link to student profile."""
    form = db.query(AdmissionForm).filter(AdmissionForm.id == form_id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    
    # Update form with ALL provided data
    all_fields = [
        # Basic Personal Details
        'student_name', 'first_name', 'middle_name', 'surname',
        'date_of_birth', 'gender', 'category', 'nationality', 'religion',
        'aadhar_number', 'blood_group', 'below_poverty_line', 'minority_category',
        
        # Academic & Admission Details
        'academic_session', 'course', 'admission_category', 'admission_category_other',
        'du_portal_form_number', 'cuet_score', 'college_roll_no', 'date_of_admission',
        'course_applied', 'application_number', 'enrollment_number', 'admission_date',
        'du_enrollment_number', 'hindi_medium_preference',
        
        # Address Details
        'permanent_address', 'permanent_address_line1', 'permanent_address_line2', 
        'permanent_address_line3', 'permanent_state', 'permanent_pincode',
        'correspondence_address', 'correspondence_address_line1', 'correspondence_address_line2',
        'correspondence_address_line3', 'correspondence_state', 'correspondence_pincode',
        'pincode', 'city', 'state',
        
        # Contact Details
        'phone_number', 'alternate_phone', 'email', 
        'emergency_contact_name', 'emergency_contact_phone',
        
        # Mother's Details
        'mother_name', 'mother_occupation', 'mother_designation', 'mother_organization',
        'mother_email', 'mother_mobile', 'mother_landline_code', 'mother_landline', 'mother_phone',
        
        # Father's Details
        'father_name', 'father_occupation', 'father_designation', 'father_organization',
        'father_email', 'father_mobile', 'father_landline_code', 'father_landline', 'father_phone',
        
        # Guardian Details
        'guardian_name', 'guardian_relation', 'guardian_residential_address', 'guardian_organization',
        'guardian_email', 'guardian_mobile', 'guardian_landline_code', 'guardian_landline', 'guardian_phone',
        
        # Family Income
        'annual_income',
        
        # Academic History
        'tenth_board', 'tenth_year', 'tenth_percentage', 'tenth_school',
        'twelfth_board', 'twelfth_year', 'twelfth_percentage', 'twelfth_school',
        'twelfth_roll_number', 'twelfth_institution', 'hindi_studied_upto',
        'previous_qualification', 'graduation_details',
        
        # Certificate Details
        'category_certificate_authority', 'category_certificate_number', 'category_certificate_date',
        'disability_percentage', 'disability_type', 'udid_number',
        
        # CUET Marks
        'cuet_subject_1', 'cuet_total_score_1', 'cuet_score_obtained_1',
        'cuet_subject_2', 'cuet_total_score_2', 'cuet_score_obtained_2',
        'cuet_subject_3', 'cuet_total_score_3', 'cuet_score_obtained_3',
        'cuet_subject_4', 'cuet_total_score_4', 'cuet_score_obtained_4',
        'cuet_subject_5', 'cuet_total_score_5', 'cuet_score_obtained_5',
        'cuet_subject_6', 'cuet_total_score_6', 'cuet_score_obtained_6',
        'cuet_total_score',
        
        # Document Checklist
        'doc_admission_form', 'doc_undertaking_ragging', 'doc_photographs',
        'doc_cuet_scorecard', 'doc_class_xii_marksheet', 'doc_class_x_certificate',
        'doc_class_xii_certificate', 'doc_character_certificate', 'doc_transfer_certificate',
        'doc_hindi_certificate', 'doc_caste_certificate', 'doc_sports_eca',
        'doc_originals', 'doc_photo_id',
    ]
    
    for field in all_fields:
        value = getattr(verification, field, None)
        if value is not None:
            # Check if the form model has this field before setting
            if hasattr(form, field):
                setattr(form, field, value)
    
    # Sync category and admission_category (they are the same field)
    if form.admission_category and not form.category:
        form.category = form.admission_category
    elif form.category and not form.admission_category:
        form.admission_category = form.category
    # If both are set, prefer admission_category as the source of truth
    elif form.admission_category:
        form.category = form.admission_category

    if verification.additional_info is not None:
        if form.additional_info is None:
            form.additional_info = {}
        form.additional_info.update(verification.additional_info)
    
    # Only update status and link profile if verify=True
    if verify and verification.student_name:
        form.status = FormStatus.VERIFIED
        if not form.verified_date:
            form.verified_date = datetime.utcnow()
        
        # Auto-link to student profile if student_name is provided
        try:
            profile = get_or_create_student_profile(
                db,
                verification.student_name,
                verification.aadhar_number
            )
            form.student_profile_id = profile.id
        except Exception as e:
            # Log error but don't fail the update
            logger.warning(f"Could not link form to student profile: {e}")
        
        # Rename file to include student name (only if not already renamed)
        try:
            from backend.utils.file_handler import rename_form_file, sanitize_filename
            
            # Check if filename already contains student name (avoid renaming multiple times)
            sanitized_name = sanitize_filename(verification.student_name).lower()
            current_filename_lower = form.filename.lower()
            
            # Only rename if filename doesn't already start with the student name pattern
            # Check if filename starts with sanitized name followed by underscore and form_id
            expected_prefix = f"{sanitized_name}_{form.id}".lower()
            
            if sanitized_name and not current_filename_lower.startswith(expected_prefix):
                new_file_path, new_filename = rename_form_file(
                    form.file_path,
                    verification.student_name,
                    form.id
                )
                form.file_path = new_file_path
                form.filename = new_filename
                logger.info(f"Renamed form {form.id} file to: {new_filename}")
        except Exception as e:
            # Log error but don't fail the update
            logger.warning(f"Could not rename form file: {e}")
        
        # Automatically create annotation from verified data (same as verify_form)
        try:
            from backend.api.routes.annotation import AnnotationField
            
            annotation_fields = []
            field_mapping = {
                'student_name': 'student_name', 'date_of_birth': 'date_of_birth',
                'gender': 'gender', 'category': 'category', 'nationality': 'nationality',
                'religion': 'religion', 'aadhar_number': 'aadhar_number',
                'blood_group': 'blood_group', 'permanent_address': 'permanent_address',
                'correspondence_address': 'correspondence_address', 'pincode': 'pincode',
                'city': 'city', 'state': 'state', 'phone_number': 'phone_number',
                'alternate_phone': 'alternate_phone', 'email': 'email',
                'emergency_contact_name': 'emergency_contact_name',
                'emergency_contact_phone': 'emergency_contact_phone',
                'father_name': 'father_name', 'father_occupation': 'father_occupation',
                'father_phone': 'father_phone', 'mother_name': 'mother_name',
                'mother_occupation': 'mother_occupation', 'mother_phone': 'mother_phone',
                'guardian_name': 'guardian_name', 'guardian_relation': 'guardian_relation',
                'guardian_phone': 'guardian_phone', 'annual_income': 'annual_income',
                'tenth_board': 'tenth_board', 'tenth_year': 'tenth_year',
                'tenth_percentage': 'tenth_percentage', 'tenth_school': 'tenth_school',
                'twelfth_board': 'twelfth_board', 'twelfth_year': 'twelfth_year',
                'twelfth_percentage': 'twelfth_percentage', 'twelfth_school': 'twelfth_school',
                'previous_qualification': 'previous_qualification',
                'graduation_details': 'graduation_details', 'course_applied': 'course_applied',
                'application_number': 'application_number', 'enrollment_number': 'enrollment_number',
                'admission_date': 'admission_date',
            }
            
            for field_key, field_name in field_mapping.items():
                value = getattr(verification, field_key, None)
                if value and str(value).strip():
                    annotation_fields.append(AnnotationField(
                        field_name=field_name,
                        value=str(value).strip(),
                        page_number=1,
                        confidence=1.0
                    ))
            
            if annotation_fields:
                key_value_pairs = {f.field_name: f.value for f in annotation_fields}
                if form.additional_info is None:
                    form.additional_info = {}
                form.additional_info['annotation'] = {
                    'fields': [f.dict() for f in annotation_fields],
                    'checkboxes': [],
                    'key_value_pairs': key_value_pairs,
                    'notes': 'Auto-created from verified form data',
                    'annotated_at': datetime.utcnow().isoformat(),
                    'annotated_by': 'update-api'
                }
        except Exception as e:
            logger.warning(f"Failed to create annotation for form {form_id}: {e}")
    
    db.commit()
    db.refresh(form)
    
    return FormDetailResponse.model_validate(form)

@router.get("/search/results", response_model=List[FormDetailResponse])
async def search_forms(
    student_name: Optional[str] = Query(None),
    phone_number: Optional[str] = Query(None),
    email: Optional[str] = Query(None),
    enrollment_number: Optional[str] = Query(None),
    application_number: Optional[str] = Query(None),
    course_applied: Optional[str] = Query(None),
    status: Optional[FormStatus] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Search forms by various criteria including enrollment number"""
    query = db.query(AdmissionForm)
    
    query = apply_form_filters(
        query,
        student_name=student_name,
        phone_number=phone_number,
        email=email,
        enrollment_number=enrollment_number,
        application_number=application_number,
        course_applied=course_applied,
        status=status,
        date_from=date_from,
        date_to=date_to,
    )
    
    # Pagination
    skip = (page - 1) * limit
    forms = query.order_by(AdmissionForm.upload_date.desc(), AdmissionForm.id.desc()).offset(skip).limit(limit).all()

    filters_snapshot = {
        "student_name": student_name,
        "phone_number": phone_number,
        "email": email,
        "enrollment_number": enrollment_number,
        "application_number": application_number,
        "course_applied": course_applied,
        "status": status.value if status else None,
        "date_from": date_from.isoformat() if date_from else None,
        "date_to": date_to.isoformat() if date_to else None,
    }
    active_filters = {key: value for key, value in filters_snapshot.items() if value}
    logger.info(
        "Search forms filters=%s page=%s limit=%s results=%s",
        active_filters,
        page,
        limit,
        len(forms),
    )
    
    # Include documents for each form
    from backend.models.document import DocumentResponse
    result = []
    for form in forms:
        form_data = FormDetailResponse.model_validate(form)
        documents = db.query(StudentDocument).filter(
            StudentDocument.form_id == form.id
        ).all()
        form_data.documents = [DocumentResponse.model_validate(doc) for doc in documents]
        result.append(form_data)
    
    return result

@router.delete("/{form_id}", status_code=204)
async def delete_form(form_id: int, db: Session = Depends(get_db)):
    """Delete a form and its associated file"""
    form = db.query(AdmissionForm).filter(AdmissionForm.id == form_id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    
    # Delete file if it exists
    import os
    from pathlib import Path
    upload_dir = Path(settings.UPLOAD_DIR).resolve()
    full_file_path = upload_dir / form.file_path
    if full_file_path.exists():
        os.remove(full_file_path)
    
    db.delete(form)
    db.commit()
    return None

