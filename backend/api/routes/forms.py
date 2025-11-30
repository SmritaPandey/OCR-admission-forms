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
            provider = get_ocr_provider(provider_name)

        selected_provider = provider_name

        # Construct full path from relative path
        import os
        from pathlib import Path
        from backend.utils.file_handler import load_all_pdf_pages, get_file_extension
        upload_dir = Path(settings.UPLOAD_DIR).resolve()
        full_file_path = upload_dir / form.file_path
        
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
        
        # Parse structured data from OCR text for SRCC forms
        if ocr_result.get('raw_text'):
            from backend.utils.form_parser import parse_form_text
            is_srcc_form = 'srcc' in (form.filename or '').lower() or 'data form' in (form.filename or '').lower()
            if is_srcc_form:
                structured_data = parse_form_text(ocr_result['raw_text'], form_type='srcc')
                ocr_result['structured_data'] = structured_data
                # Auto-fill all form fields if available
                for field in ['student_name', 'date_of_birth', 'gender', 'category', 'nationality', 
                             'religion', 'aadhar_number', 'blood_group', 'permanent_address', 
                             'correspondence_address', 'pincode', 'city', 'state', 'phone_number', 
                             'alternate_phone', 'email', 'emergency_contact_name', 'emergency_contact_phone',
                             'father_name', 'father_occupation', 'father_phone', 'mother_name', 
                             'mother_occupation', 'mother_phone', 'guardian_name', 'guardian_relation', 
                             'guardian_phone', 'annual_income', 'tenth_board', 'tenth_year', 
                             'tenth_percentage', 'tenth_school', 'twelfth_board', 'twelfth_year', 
                             'twelfth_percentage', 'twelfth_school', 'previous_qualification', 
                             'graduation_details', 'course_applied', 'application_number', 'enrollment_number', 'admission_date']:
                    if structured_data.get(field):
                        setattr(form, field, structured_data[field])
        
        form.extracted_data = ocr_result
        form.ocr_provider = selected_provider
        form.status = FormStatus.EXTRACTED
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
    
    # Update form with verified data - all fields
    # Basic Details
    for field in ['student_name', 'date_of_birth', 'gender', 'category', 'nationality', 
                  'religion', 'aadhar_number', 'blood_group']:
        setattr(form, field, getattr(verification, field, None))
    
    # Address Details
    for field in ['permanent_address', 'correspondence_address', 'pincode', 'city', 'state']:
        setattr(form, field, getattr(verification, field, None))
    
    # Contact Details
    for field in ['phone_number', 'alternate_phone', 'email', 'emergency_contact_name', 
                 'emergency_contact_phone']:
        setattr(form, field, getattr(verification, field, None))
    
    # Guardian/Parent Details
    for field in ['father_name', 'father_occupation', 'father_phone', 'mother_name', 
                 'mother_occupation', 'mother_phone', 'guardian_name', 'guardian_relation', 
                 'guardian_phone', 'annual_income']:
        setattr(form, field, getattr(verification, field, None))
    
    # Educational Qualifications
    for field in ['tenth_board', 'tenth_year', 'tenth_percentage', 'tenth_school',
                 'twelfth_board', 'twelfth_year', 'twelfth_percentage', 'twelfth_school',
                 'previous_qualification', 'graduation_details']:
        setattr(form, field, getattr(verification, field, None))
    
    # Course Application Details
    for field in ['course_applied', 'application_number', 'enrollment_number', 'admission_date']:
        setattr(form, field, getattr(verification, field, None))
    
    form.additional_info = verification.additional_info
    
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
            print(f"Warning: Could not link form to student profile: {e}")
    
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
    db: Session = Depends(get_db)
):
    """Update form data (without requiring verification status)"""
    form = db.query(AdmissionForm).filter(AdmissionForm.id == form_id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    
    # Update form with provided data
    for field in ['student_name', 'date_of_birth', 'gender', 'category', 'nationality',
                  'religion', 'aadhar_number', 'blood_group',
                  'permanent_address', 'correspondence_address', 'pincode', 'city', 'state',
                  'phone_number', 'alternate_phone', 'email', 'emergency_contact_name',
                  'emergency_contact_phone', 'father_name', 'father_occupation', 'father_phone',
                  'mother_name', 'mother_occupation', 'mother_phone', 'guardian_name',
                  'guardian_relation', 'guardian_phone', 'annual_income', 'tenth_board',
                  'tenth_year', 'tenth_percentage', 'tenth_school', 'twelfth_board',
                  'twelfth_year', 'twelfth_percentage', 'twelfth_school', 'previous_qualification',
                  'graduation_details', 'course_applied', 'application_number',
                  'enrollment_number', 'admission_date']:
        value = getattr(verification, field, None)
        if value is not None:
            setattr(form, field, value)

    if verification.additional_info is not None:
        form.additional_info = verification.additional_info
    
    # Update status if student_name is provided (mark as verified)
    if verification.student_name:
        form.status = FormStatus.VERIFIED
        if not form.verified_date:
            form.verified_date = datetime.utcnow()
    
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

