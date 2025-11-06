from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
from backend.database import get_db, AdmissionForm, FormStatus
from backend.utils.file_handler import save_uploaded_file, load_image
from backend.ocr import get_ocr_provider
from backend.models.form import FormResponse
from backend.config import settings
from datetime import datetime

router = APIRouter()

@router.post("/upload", response_model=FormResponse, status_code=201)
async def upload_form(
    file: UploadFile = File(...),
    ocr_provider: str = None,
    db: Session = Depends(get_db)
):
    """
    Upload a scanned admission form and automatically extract text using OCR
    """
    try:
        # Save uploaded file
        file_path, filename = await save_uploaded_file(file)
        
        # Determine OCR provider
        provider_name = ocr_provider or "tesseract"
        
        # Create form record - store relative path for file serving
        # Convert absolute path to relative path from uploads directory
        import os
        from pathlib import Path
        upload_dir = Path(settings.UPLOAD_DIR).resolve()
        file_path_obj = Path(file_path).resolve()
        
        # Store relative path for serving files
        relative_path = os.path.relpath(file_path_obj, upload_dir)
        
        form = AdmissionForm(
            filename=file.filename or filename,
            file_path=relative_path,  # Store relative path
            ocr_provider=provider_name if provider_name != "best" else "multi",  # Store actual provider used
            status=FormStatus.EXTRACTING
        )
        db.add(form)
        db.commit()
        db.refresh(form)
        
        # Perform OCR extraction
        try:
            # Check if it's a PDF - process all pages
            file_ext = file.filename.split('.')[-1].lower() if file.filename else ""
            is_pdf = file_ext == 'pdf'
            
            if is_pdf:
                # Load all pages from PDF
                from backend.utils.file_handler import load_all_pdf_pages
                pages = load_all_pdf_pages(file_path)
                
                # Process each page with OCR and combine results
                all_raw_text = []
                all_confidences = []
                page_results = []
                
                provider = get_ocr_provider(provider_name) if provider_name != "best" else None
                
                for page_num, page_image in enumerate(pages):
                    try:
                        # Handle multi-provider "best" mode
                        if provider_name == "best":
                            from backend.ocr.multi_provider import MultiProviderOCR
                            multi_ocr = MultiProviderOCR()
                            page_result = await multi_ocr.extract_with_best_provider(page_image)
                            if page_num == 0:
                                form.ocr_provider = page_result.get('provider_used', 'multi')
                        else:
                            # Use enhanced OCR extraction with preprocessing
                            if provider_name == "tesseract":
                                page_result = await provider.extract_text(page_image, preprocess=True)
                            else:
                                page_result = await provider.extract_text(page_image)
                        
                        # Collect text and confidence from each page
                        if page_result.get('raw_text'):
                            all_raw_text.append(f"\n--- Page {page_num + 1} ---\n{page_result['raw_text']}")
                            if page_result.get('confidence'):
                                all_confidences.append(page_result['confidence'])
                        
                        page_results.append({
                            'page': page_num + 1,
                            'raw_text': page_result.get('raw_text', ''),
                            'confidence': page_result.get('confidence', 0.0)
                        })
                        
                    except Exception as page_error:
                        # Continue with other pages if one fails
                        print(f"Error processing page {page_num + 1}: {str(page_error)}")
                        continue
                
                # Combine all pages' text
                combined_text = "\n".join(all_raw_text)
                avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0
                
                ocr_result = {
                    "raw_text": combined_text,
                    "confidence": round(avg_confidence, 2),
                    "structured_data": None,
                    "provider": form.ocr_provider,
                    "pages_processed": len(pages),
                    "page_results": page_results
                }
            else:
                # Single image file - process normally
                image = load_image(file_path)
                
                # Handle multi-provider "best" mode
                if provider_name == "best":
                    from backend.ocr.multi_provider import MultiProviderOCR
                    multi_ocr = MultiProviderOCR()
                    ocr_result = await multi_ocr.extract_with_best_provider(image)
                    # Update provider name to the one that was actually used
                    form.ocr_provider = ocr_result.get('provider_used', 'multi')
                else:
                    provider = get_ocr_provider(provider_name)
                    # Use enhanced OCR extraction with preprocessing
                    # For Tesseract, pass preprocess=True for better results
                    if provider_name == "tesseract":
                        ocr_result = await provider.extract_text(image, preprocess=True)
                    else:
                        ocr_result = await provider.extract_text(image)
            
            # Parse structured data from OCR text for SRCC forms
            if ocr_result.get('raw_text'):
                from backend.utils.form_parser import parse_form_text
                # Check if this is an SRCC form based on filename pattern
                is_srcc_form = 'srcc' in (file.filename or '').lower() or 'data form' in (file.filename or '').lower()
                if is_srcc_form:
                    structured_data = parse_form_text(ocr_result['raw_text'], form_type='srcc')
                    ocr_result['structured_data'] = structured_data
                    # Auto-fill all form fields if available
                    # Basic Details
                    for field in ['student_name', 'date_of_birth', 'gender', 'category', 'nationality', 
                                 'religion', 'aadhar_number', 'blood_group']:
                        if structured_data.get(field):
                            setattr(form, field, structured_data[field])
                    
                    # Address Details
                    for field in ['permanent_address', 'correspondence_address', 'pincode', 'city', 'state']:
                        if structured_data.get(field):
                            setattr(form, field, structured_data[field])
                    
                    # Contact Details
                    for field in ['phone_number', 'alternate_phone', 'email', 'emergency_contact_name', 
                                 'emergency_contact_phone']:
                        if structured_data.get(field):
                            setattr(form, field, structured_data[field])
                    
                    # Guardian/Parent Details
                    for field in ['father_name', 'father_occupation', 'father_phone', 'mother_name', 
                                 'mother_occupation', 'mother_phone', 'guardian_name', 'guardian_relation', 
                                 'guardian_phone', 'annual_income']:
                        if structured_data.get(field):
                            setattr(form, field, structured_data[field])
                    
                    # Educational Qualifications
                    for field in ['tenth_board', 'tenth_year', 'tenth_percentage', 'tenth_school',
                                 'twelfth_board', 'twelfth_year', 'twelfth_percentage', 'twelfth_school',
                                 'previous_qualification', 'graduation_details']:
                        if structured_data.get(field):
                            setattr(form, field, structured_data[field])
                    
                    # Course Application Details
                    for field in ['course_applied', 'application_number', 'admission_date']:
                        if structured_data.get(field):
                            setattr(form, field, structured_data[field])
            
            # Update form with extracted data
            form.extracted_data = ocr_result
            form.status = FormStatus.EXTRACTED
            db.commit()
            
        except Exception as e:
            form.status = FormStatus.ERROR
            db.commit()
            raise HTTPException(status_code=500, detail=f"OCR extraction failed: {str(e)}")
        
        return FormResponse.model_validate(form)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.post("/pages", response_model=FormResponse, status_code=201)
async def upload_form_pages(
    files: List[UploadFile] = File(...),
    ocr_provider: str = None,
    db: Session = Depends(get_db)
):
    """
    Upload multiple scanned pages/images for a single admission form.
    All pages will be processed together for OCR extraction.
    """
    if not files or len(files) == 0:
        raise HTTPException(status_code=400, detail="At least one file is required")
    
    try:
        from backend.utils.file_handler import save_uploaded_file, load_image, get_file_extension
        from pathlib import Path
        import os
        
        # Determine OCR provider
        provider_name = ocr_provider or "tesseract"
        
        # Save all files and collect paths
        saved_files = []
        pages = []
        
        for file in files:
            # Save uploaded file
            file_path, filename = await save_uploaded_file(file)
            
            # Load image
            file_ext = get_file_extension(file_path)
            if file_ext == 'pdf':
                from backend.utils.file_handler import load_all_pdf_pages
                pdf_pages = load_all_pdf_pages(file_path)
                pages.extend(pdf_pages)
            else:
                image = load_image(file_path)
                pages.append(image)
            
            saved_files.append((file_path, filename))
        
        # Use first file's name for the form record
        first_file_path, first_filename = saved_files[0]
        upload_dir = Path(settings.UPLOAD_DIR).resolve()
        file_path_obj = Path(first_file_path).resolve()
        relative_path = os.path.relpath(file_path_obj, upload_dir)
        
        # Create form record
        form = AdmissionForm(
            filename=files[0].filename or first_filename,
            file_path=relative_path,
            ocr_provider=provider_name if provider_name != "best" else "multi",
            status=FormStatus.EXTRACTING
        )
        db.add(form)
        db.commit()
        db.refresh(form)
        
        # Perform OCR extraction on all pages
        try:
            all_raw_text = []
            all_confidences = []
            page_results = []
            
            provider = get_ocr_provider(provider_name) if provider_name != "best" else None
            
            for page_num, page_image in enumerate(pages):
                try:
                    # Handle multi-provider "best" mode
                    if provider_name == "best":
                        from backend.ocr.multi_provider import MultiProviderOCR
                        multi_ocr = MultiProviderOCR()
                        page_result = await multi_ocr.extract_with_best_provider(page_image)
                        if page_num == 0:
                            form.ocr_provider = page_result.get('provider_used', 'multi')
                    else:
                        # Use enhanced OCR extraction with preprocessing
                        if provider_name == "tesseract":
                            page_result = await provider.extract_text(page_image, preprocess=True)
                        else:
                            page_result = await provider.extract_text(page_image)
                    
                    # Collect text and confidence from each page
                    if page_result.get('raw_text'):
                        all_raw_text.append(f"\n--- Page {page_num + 1} ---\n{page_result['raw_text']}")
                        if page_result.get('confidence'):
                            all_confidences.append(page_result['confidence'])
                    
                    page_results.append({
                        'page': page_num + 1,
                        'raw_text': page_result.get('raw_text', ''),
                        'confidence': page_result.get('confidence', 0.0)
                    })
                    
                except Exception as page_error:
                    print(f"Error processing page {page_num + 1}: {str(page_error)}")
                    continue
            
            # Combine all pages' text
            combined_text = "\n".join(all_raw_text)
            avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0
            
            ocr_result = {
                "raw_text": combined_text,
                "confidence": round(avg_confidence, 2),
                "structured_data": None,
                "provider": form.ocr_provider,
                "pages_processed": len(pages),
                "page_results": page_results
            }
            
            # Parse structured data from OCR text for SRCC forms
            if ocr_result.get('raw_text'):
                from backend.utils.form_parser import parse_form_text
                is_srcc_form = 'srcc' in (files[0].filename or '').lower() or 'data form' in (files[0].filename or '').lower()
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
                                 'graduation_details', 'course_applied', 'application_number', 'admission_date']:
                        if structured_data.get(field):
                            setattr(form, field, structured_data[field])
            
            # Update form with extracted data
            form.extracted_data = ocr_result
            form.status = FormStatus.EXTRACTED
            db.commit()
            
        except Exception as e:
            form.status = FormStatus.ERROR
            db.commit()
            raise HTTPException(status_code=500, detail=f"OCR extraction failed: {str(e)}")
        
        return FormResponse.model_validate(form)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.get("/providers")
async def list_ocr_providers():
    """Get list of available OCR providers"""
    from backend.ocr.ocr_factory import OCRFactory
    available = OCRFactory.get_available_providers()
    # Add "best" option if multiple providers are available
    if len(available) > 1:
        available.append("best")  # Multi-provider mode
    return {"providers": available, "default": "tesseract"}

