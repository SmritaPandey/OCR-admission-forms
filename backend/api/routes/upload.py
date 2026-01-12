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
        provider_name = (ocr_provider or settings.OCR_PROVIDER).lower()
        
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
                import fitz  # PyMuPDF
                from pathlib import Path
                
                all_pages = load_all_pdf_pages(file_path)
                total_pages = len(all_pages)
                
                # Split: first 4 pages = form, rest = documents
                FORM_PAGES = 4
                form_pages = all_pages[:FORM_PAGES] if total_pages > FORM_PAGES else all_pages
                document_pages = all_pages[FORM_PAGES:] if total_pages > FORM_PAGES else []
                
                # Process form pages (first 4) with OCR
                all_raw_text = []
                all_confidences = []
                page_results = []
                
                provider = get_ocr_provider(provider_name) if provider_name != "best" else None
                
                for page_num, page_image in enumerate(form_pages):
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
                # Note: Page order doesn't matter - extraction is page-order agnostic
                combined_text = "\n".join(all_raw_text)
                avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0
                
                # Optional: Detect and log page types for debugging
                try:
                    from backend.utils.page_detector import PageDetector
                    detected_pages = PageDetector.detect_pages_from_text(combined_text)
                    if detected_pages:
                        page_types = {p['page_number']: p.get('page_type', 'unknown') for p in detected_pages}
                        # Log if pages are out of order
                        expected_order = {1: 'page1', 2: 'page2', 3: 'page3', 4: 'page4'}
                        out_of_order = any(
                            page_types.get(num) != expected_order.get(num)
                            for num in page_types.keys()
                            if num <= 4
                        )
                        if out_of_order:
                            print(f"⚠️  Pages detected out of order: {page_types}")
                except Exception as e:
                    # Non-critical - continue even if page detection fails
                    print(f"Page detection warning: {e}")
                
                ocr_result = {
                    "raw_text": combined_text,
                    "confidence": round(avg_confidence, 2),
                    "structured_data": None,
                    "provider": form.ocr_provider,
                    "pages_processed": len(form_pages),
                    "total_pages": total_pages,
                    "document_pages_count": len(document_pages),
                    "page_results": page_results
                }
                
                # Save remaining pages as attached documents
                if document_pages:
                    try:
                        from backend.database import StudentDocument, DocumentCategory
                        from backend.utils.file_handler import save_document_file
                        from datetime import datetime
                        
                        # Open original PDF to extract pages
                        pdf_document = fitz.open(file_path)
                        
                        # Create a new PDF with remaining pages
                        doc_pdf = fitz.open()
                        for page_idx in range(FORM_PAGES, len(pdf_document)):
                            doc_pdf.insert_pdf(pdf_document, from_page=page_idx, to_page=page_idx)
                        
                        # Save the document PDF
                        upload_dir = Path(settings.UPLOAD_DIR)
                        doc_filename = f"{Path(file_path).stem}_pages_{FORM_PAGES + 1}-{total_pages}.pdf"
                        doc_path = upload_dir / "documents" / doc_filename
                        doc_path.parent.mkdir(parents=True, exist_ok=True)
                        doc_pdf.save(str(doc_path))
                        doc_pdf.close()
                        pdf_document.close()
                        
                        # Calculate file size
                        doc_file_size = doc_path.stat().st_size
                        doc_relative_path = os.path.relpath(doc_path, upload_dir)
                        
                        # Create document record
                        document = StudentDocument(
                            filename=doc_filename,
                            file_path=doc_relative_path,
                            document_category=DocumentCategory.OTHER,
                            description=f"Pages {FORM_PAGES + 1}-{total_pages} from uploaded form",
                            file_size=doc_file_size,
                            form_id=form.id
                        )
                        db.add(document)
                        db.commit()
                        
                    except Exception as doc_error:
                        # Log error but don't fail the form upload
                        print(f"Warning: Failed to save document pages: {str(doc_error)}")
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
            
            # Parse structured data from OCR text - ALWAYS extract (SRCC extractor works for all forms)
            if ocr_result.get('raw_text'):
                from backend.utils.srcc_form_extractor import extract_srcc_form
                # Always use SRCC extractor - it's the most comprehensive extractor
                structured_data = extract_srcc_form(ocr_result['raw_text'])
                ocr_result['structured_data'] = structured_data
                print(f"[Upload] Extracted {len(structured_data)} fields from OCR text")
                
                # Auto-fill ALL form fields automatically using helper function
                from backend.utils.form_field_applier import apply_structured_data_to_form
                fields_set = apply_structured_data_to_form(form, structured_data)
                print(f"[Upload] Applied {fields_set} fields from structured_data to form {form.id}")
            
            # Update form with extracted data
            form.extracted_data = ocr_result
            form.status = FormStatus.EXTRACTED
            
            # Commit form with all fields applied
            db.commit()
            db.refresh(form)  # Refresh to ensure form object has latest data
            
        except Exception as e:
            form.status = FormStatus.ERROR
            db.commit()
            error_msg = str(e)
            # Provide more helpful error messages
            if "tesseract" in error_msg.lower() and "not found" in error_msg.lower():
                error_msg = "Tesseract OCR is not installed or not found. Please install Tesseract OCR and ensure it's in your PATH or set TESSERACT_CMD environment variable."
            elif "broken data stream" in error_msg.lower() or ("invalid" in error_msg.lower() and "image" in error_msg.lower()):
                error_msg = f"Image file is corrupted or invalid: {error_msg}"
            raise HTTPException(status_code=500, detail=f"OCR extraction failed: {error_msg}")
        
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
        provider_name = (ocr_provider or settings.OCR_PROVIDER).lower()
        
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
                # NOTE: Extraction is page-order agnostic - works correctly even if pages 2 and 3 are swapped
                combined_text = "\n".join(all_raw_text)
                avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0
                
                # Optional: Detect and log page types for debugging (non-critical)
                try:
                    from backend.utils.page_detector import PageDetector
                    detected_pages = PageDetector.detect_pages_from_text(combined_text)
                    if detected_pages:
                        page_types = {p['page_number']: p.get('page_type', 'unknown') for p in detected_pages}
                        # Log if pages are out of order (for debugging)
                        expected_order = {1: 'page1', 2: 'page2', 3: 'page3', 4: 'page4'}
                        out_of_order = any(
                            page_types.get(num) != expected_order.get(num)
                            for num in page_types.keys()
                            if num <= 4
                        )
                        if out_of_order:
                            print(f"ℹ️  Pages detected out of order: {page_types} (extraction will still work correctly)")
                except Exception as e:
                    # Non-critical - continue even if page detection fails
                    pass
                
                ocr_result = {
                "raw_text": combined_text,
                "confidence": round(avg_confidence, 2),
                "structured_data": None,
                "provider": form.ocr_provider,
                "pages_processed": len(pages),
                "page_results": page_results
            }
            
            # Parse structured data from OCR text for SRCC forms using advanced extractor
            if ocr_result.get('raw_text'):
                from backend.utils.srcc_form_extractor import extract_srcc_form
                # Always use SRCC extractor - it's the most comprehensive extractor
                structured_data = extract_srcc_form(ocr_result['raw_text'])
                ocr_result['structured_data'] = structured_data
                print(f"[Upload Pages] Extracted {len(structured_data)} fields from OCR text")
                
                # Auto-fill ALL form fields automatically using helper function
                from backend.utils.form_field_applier import apply_structured_data_to_form
                fields_set = apply_structured_data_to_form(form, structured_data)
                print(f"[Upload Pages] Applied {fields_set} fields from structured_data to form {form.id}")
            
            # Update form with extracted data
            form.extracted_data = ocr_result
            form.status = FormStatus.EXTRACTED
            
            # Commit form with all fields applied
            db.commit()
            db.refresh(form)  # Refresh to ensure form object has latest data
            
        except Exception as e:
            form.status = FormStatus.ERROR
            db.commit()
            error_msg = str(e)
            # Provide more helpful error messages
            if "tesseract" in error_msg.lower() and "not found" in error_msg.lower():
                error_msg = "Tesseract OCR is not installed or not found. Please install Tesseract OCR and ensure it's in your PATH or set TESSERACT_CMD environment variable."
            elif "broken data stream" in error_msg.lower() or ("invalid" in error_msg.lower() and "image" in error_msg.lower()):
                error_msg = f"Image file is corrupted or invalid: {error_msg}"
            raise HTTPException(status_code=500, detail=f"OCR extraction failed: {error_msg}")
        
        return FormResponse.model_validate(form)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.get("/providers")
async def list_ocr_providers():
    """
    Get list of available OCR providers and their capabilities
    
    For Azure Form Recognizer, includes information about custom models.
    See: https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/train/custom-model
    """
    from backend.ocr.ocr_factory import OCRFactory, get_ocr_provider
    available = OCRFactory.get_available_providers()
    # Add "best" option if multiple providers are available
    if len(available) > 1:
        available.append("best")  # Multi-provider mode
    
    # Prefer google-vision as default (best trained and most accurate)
    if "google-vision" in available:
        default_provider = "google-vision"
    else:
        default_provider = settings.OCR_PROVIDER.lower()
        if default_provider not in available:
            default_provider = available[0] if available else "tesseract"
    
    # Get model information for Azure Form Recognizer if available
    model_info = None
    if "azure-form-recognizer" in available:
        try:
            provider = get_ocr_provider("azure-form-recognizer")
            if hasattr(provider, 'get_model_info'):
                model_info = provider.get_model_info()
        except Exception:
            pass
    
    return {
        "providers": available,
        "default": default_provider,
        "model_info": model_info  # Azure custom model information if available
    }

