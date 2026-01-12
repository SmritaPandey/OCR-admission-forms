"""
Batch Upload API Routes
Handle batch processing of multiple forms (especially 3-page forms)
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from backend.database import get_db, AdmissionForm, FormStatus
from backend.utils.file_handler import save_uploaded_file, load_all_pdf_pages
from backend.utils.multi_page_handler import MultiPageFormHandler
from backend.utils.batch_processor import batch_processor, JobStatus
from backend.ocr import get_ocr_provider
from backend.config import settings
from backend.models.form import FormResponse
from pathlib import Path
import os

router = APIRouter()

@router.post("/batch-upload", status_code=202)
async def batch_upload_forms(
    files: List[UploadFile] = File(...),
    ocr_provider: Optional[str] = Form(None),
    pages_per_form: int = Form(3),
    db: Session = Depends(get_db)  # Not used in function, but kept for consistency
):
    """
    Upload multiple forms in batch for processing.
    Each form should be a PDF with specified number of pages (default: 3).
    Returns a job ID for tracking progress.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    # Validate files are PDFs
    for file in files:
        file_ext = file.filename.split('.')[-1].lower() if file.filename else ""
        if file_ext != 'pdf':
            raise HTTPException(
                status_code=400,
                detail=f"All files must be PDFs. Found: {file_ext}"
            )
    
    # Determine OCR provider (default to craft-trocr for handwritten forms)
    provider_name = ocr_provider or "craft-trocr"
    
    async def process_form(file_item: UploadFile) -> dict:
        """Process a single form file"""
        # Create new DB session for this task
        from backend.database import SessionLocal
        local_db = SessionLocal()
        try:
            # Save file
            file_path, filename = await save_uploaded_file(file_item)
            
            # Load all pages from PDF
            pages = load_all_pdf_pages(file_path)
            
            # Validate minimum page count (at least 1 page for form)
            if len(pages) < 1:
                return {
                    "filename": file_item.filename,
                    "status": "error",
                    "error": "PDF has no pages"
                }
            
            # Note: We process first 4 pages as form, rest as documents
            # So we don't strictly require exact page count
            
            # Get OCR provider (support all providers including craft, trocr, craft-trocr)
            if provider_name == "best":
                from backend.ocr.multi_provider import MultiProviderOCR
                multi_ocr = MultiProviderOCR()
                # Process first 4 pages as form
                FORM_PAGES = 4
                form_pages = pages[:FORM_PAGES] if len(pages) > FORM_PAGES else pages
                
                # Process form pages with best provider
                all_raw_text = []
                all_confidences = []
                page_results = []
                
                for page_num, page_image in enumerate(form_pages, 1):
                    try:
                        page_result = await multi_ocr.extract_with_best_provider(page_image)
                        if page_result.get('raw_text'):
                            all_raw_text.append(f"\n--- Page {page_num} ---\n{page_result['raw_text']}")
                            if page_result.get('confidence'):
                                all_confidences.append(page_result['confidence'])
                        
                        page_results.append({
                            'page': page_num,
                            'raw_text': page_result.get('raw_text', ''),
                            'confidence': page_result.get('confidence', 0.0),
                            'provider': page_result.get('provider_used', 'multi')
                        })
                    except Exception as e:
                        print(f"Error processing page {page_num}: {e}")
                        continue
                
                combined_text = "\n".join(all_raw_text)
                avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0
                
                ocr_result = {
                    "raw_text": combined_text,
                    "confidence": round(avg_confidence, 2),
                    "provider": "multi",
                    "pages_processed": len(form_pages),
                    "total_pages": len(pages),
                    "document_pages_count": max(0, len(pages) - FORM_PAGES),
                    "page_results": page_results
                }
            else:
                provider = get_ocr_provider(provider_name)
                
                # Process first 4 pages as form, rest as documents
                FORM_PAGES = 4
                form_pages = pages[:FORM_PAGES] if len(pages) > FORM_PAGES else pages
                
                # Process form pages with selected provider
                all_raw_text = []
                all_confidences = []
                page_results = []
                
                for page_num, page_image in enumerate(form_pages, 1):
                    try:
                        # Use preprocessing for tesseract
                        if provider_name == "tesseract":
                            page_result = await provider.extract_text(page_image, preprocess=True)
                        else:
                            page_result = await provider.extract_text(page_image)
                        
                        if page_result.get('raw_text'):
                            all_raw_text.append(f"\n--- Page {page_num} ---\n{page_result['raw_text']}")
                            if page_result.get('confidence'):
                                all_confidences.append(page_result['confidence'])
                        
                        page_results.append({
                            'page': page_num,
                            'raw_text': page_result.get('raw_text', ''),
                            'confidence': page_result.get('confidence', 0.0),
                            'provider': page_result.get('provider', provider_name)
                        })
                    except Exception as e:
                        print(f"Error processing page {page_num}: {e}")
                        continue
                
                combined_text = "\n".join(all_raw_text)
                avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0
                
                ocr_result = {
                    "raw_text": combined_text,
                    "confidence": round(avg_confidence, 2),
                    "provider": provider_name,
                    "pages_processed": len(form_pages),
                    "total_pages": len(pages),
                    "document_pages_count": max(0, len(pages) - FORM_PAGES),
                    "page_results": page_results
                }
            
            # Parse structured data from OCR text - ALWAYS extract (SRCC extractor works for all forms)
            if ocr_result.get('raw_text'):
                from backend.utils.srcc_form_extractor import extract_srcc_form
                # Always use SRCC extractor - it's the most comprehensive extractor
                structured_data = extract_srcc_form(ocr_result['raw_text'])
                ocr_result['structured_data'] = structured_data
                print(f"[Batch Upload] Extracted {len(structured_data)} fields from OCR text")
            
            # Create form record
            upload_dir = Path(settings.UPLOAD_DIR).resolve()
            file_path_obj = Path(file_path).resolve()
            relative_path = os.path.relpath(file_path_obj, upload_dir)
            
            form = AdmissionForm(
                filename=file_item.filename or filename,
                file_path=relative_path,
                ocr_provider=ocr_result.get("provider", provider_name),
                status=FormStatus.EXTRACTING,  # Will be updated to EXTRACTED after field application
                extracted_data={
                    "raw_text": ocr_result.get("raw_text", ""),
                    "confidence": ocr_result.get("confidence", 0),
                    "structured_data": ocr_result.get("structured_data", {}),
                    "pages_processed": ocr_result.get("pages_processed", len(pages)),
                    "total_pages": ocr_result.get("total_pages", len(pages)),
                    "document_pages_count": ocr_result.get("document_pages_count", 0),
                    "page_results": ocr_result.get("page_results", [])
                }
            )
            local_db.add(form)
            local_db.commit()
            local_db.refresh(form)
            
            # Auto-fill ALL form fields automatically using helper function
            if ocr_result.get('structured_data'):
                from backend.utils.form_field_applier import apply_structured_data_to_form
                fields_set = apply_structured_data_to_form(form, ocr_result['structured_data'])
                print(f"[Batch Upload] Applied {fields_set} fields from structured_data to form {form.id}")
            
            # Update status and commit
            form.status = FormStatus.EXTRACTED
            local_db.commit()
            local_db.refresh(form)
            
            form_id = form.id
            
            return {
                "filename": file_item.filename,
                "form_id": form_id,
                "status": "success",
                "confidence": ocr_result.get("confidence", 0)
            }
            
        except Exception as e:
            return {
                "filename": file_item.filename,
                "status": "error",
                "error": str(e)
            }
        finally:
            local_db.close()
    
    # Start batch processing
    job_id = await batch_processor.process_batch(files, process_func=process_form)
    
    return {
        "job_id": job_id,
        "total_files": len(files),
        "status": "processing",
        "message": f"Batch upload started. Use /api/batch-upload/{job_id}/status to check progress"
    }

@router.get("/batch-upload/{job_id}/status")
async def get_batch_job_status(job_id: str):
    """Get status of a batch upload job"""
    job = batch_processor.get_job_status(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "job_id": job.job_id,
        "status": job.status.value,
        "total_items": job.total_items,
        "processed_items": job.processed_items,
        "successful_items": job.successful_items,
        "failed_items": job.failed_items,
        "progress_percentage": job.progress_percentage,
        "created_at": job.created_at.isoformat(),
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "errors": job.errors[:10] if job.errors else [],  # Limit errors in response
        "results": job.results[-10:] if job.results else []  # Last 10 results
    }

@router.get("/batch-upload/{job_id}/results")
async def get_batch_job_results(job_id: str, page: int = Query(1, ge=1), limit: int = Query(50, ge=1, le=100)):
    """Get detailed results from a batch upload job"""
    job = batch_processor.get_job_status(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    skip = (page - 1) * limit
    results = job.results[skip:skip + limit] if job.results else []
    
    return {
        "job_id": job.job_id,
        "status": job.status.value,
        "total_results": len(job.results) if job.results else 0,
        "page": page,
        "limit": limit,
        "results": results
    }

@router.delete("/batch-upload/{job_id}")
async def cancel_batch_job(job_id: str):
    """Cancel a batch upload job"""
    success = batch_processor.cancel_job(job_id)
    
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Job not found or cannot be cancelled"
        )
    
    return {
        "job_id": job_id,
        "status": "cancelled",
        "message": "Job cancelled successfully"
    }

@router.get("/batch-upload/jobs/list")
async def list_batch_jobs(
    status: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100)
):
    """List all batch upload jobs"""
    all_jobs = batch_processor.get_all_jobs()
    
    # Filter by status if provided
    if status:
        try:
            status_enum = JobStatus(status.lower())
            all_jobs = [j for j in all_jobs if j.get("status") == status_enum.value]
        except ValueError:
            pass
    
    # Sort by created_at (newest first) and limit
    all_jobs.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    all_jobs = all_jobs[:limit]
    
    return {
        "total_jobs": len(all_jobs),
        "jobs": all_jobs
    }
