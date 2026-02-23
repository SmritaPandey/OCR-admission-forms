"""
Batch Upload API Routes
Handle batch processing of multiple forms (especially 3-page forms)
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query, Form, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from backend.database import get_db, AdmissionForm, FormStatus
from backend.utils.file_handler import save_uploaded_file, load_all_pdf_pages, save_pdf_page_as_document
from backend.utils.multi_page_handler import MultiPageFormHandler
from backend.utils.batch_processor import batch_processor, JobStatus, BatchJob, BatchJob
from backend.ocr import get_ocr_provider
from backend.config import settings
from backend.models.form import FormResponse
from backend.api.dependencies import RequireStaffOrAdmin
from backend.models.auth_models import CurrentUser
from pathlib import Path
import os
import logging
import asyncio

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/batch-upload", status_code=202)
async def batch_upload_forms(
    files: List[UploadFile] = File(...),
    ocr_provider: Optional[str] = Form(None),
    pages_per_form: int = Form(4),  # Match FORM_PAGE_COUNT; form pages 1–4, docs 5+
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(RequireStaffOrAdmin),
):
    """
    Upload multiple forms in batch for processing.
    Each form should be a PDF with specified number of pages (default: 4).
    Pages 1–4 = form; pages 5+ = supporting documents. Returns a job ID for tracking progress.
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
    
    # CRITICAL: Save all files FIRST before starting background processing
    # This ensures file streams are read before the request completes
    saved_files = []
    for file_item in files:
        try:
            file_path, filename = await save_uploaded_file(file_item)
            saved_files.append({
                "file_path": file_path,
                "filename": filename,
                "original_filename": file_item.filename
            })
        except Exception as e:
            logger.error(f"Failed to save file {file_item.filename}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to save file {file_item.filename}: {str(e)}")
    
    # Now create a process function that works with saved file paths
    async def process_form(file_info: dict) -> dict:
        """Process a single form file using saved file path"""
        # Create new DB session for this task
        from backend.database import SessionLocal
        from pathlib import Path
        import os
        
        local_db = SessionLocal()
        try:
            file_path = file_info["file_path"]
            filename = file_info["filename"]
            original_filename = file_info["original_filename"]
            
            # pages_per_form is captured from the outer scope
            
            # Get relative path for database storage
            upload_dir = Path(settings.UPLOAD_DIR).resolve()
            file_path_obj = Path(file_path).resolve()
            relative_path = os.path.relpath(file_path_obj, upload_dir)
            
            # Create form record in database
            form = AdmissionForm(
                filename=original_filename or filename,
                file_path=relative_path,
                ocr_provider=provider_name if provider_name != "best" else "multi",
                status=FormStatus.EXTRACTING
            )
            local_db.add(form)
            local_db.commit()
            local_db.refresh(form)
            
            # Perform OCR extraction using unified pipeline
            from backend.utils.extraction_pipeline import run_enhanced_extraction
            
            # Note: run_enhanced_extraction commits to DB and updates the form
            ocr_result = await run_enhanced_extraction(form, local_db, provider_name if provider_name != "best" else None)
            
            # Refresh form to get updated data from extraction
            local_db.refresh(form)
            
            # Auto-create student profile if student_name was extracted
            # This ensures students appear in the students page immediately
            profile = None
            if form.student_name and form.student_name.strip():
                try:
                    from backend.api.routes.students import get_or_create_student_profile
                    profile = get_or_create_student_profile(
                        local_db,
                        student_name=form.student_name.strip(),
                        aadhar_number=form.aadhar_number,
                        roll_number=form.college_roll_no
                    )
                    # Link form to profile
                    if not form.student_profile_id or form.student_profile_id != profile.id:
                        form.student_profile_id = profile.id
                        local_db.commit()
                        logger.info(f"Auto-created/linked student profile {profile.id} for form {form.id} ({form.student_name})")
                except Exception as profile_error:
                    # Log but don't fail the batch upload if profile creation fails
                    logger.warning(f"Failed to create student profile for form {form.id}: {profile_error}", exc_info=True)
                    # Don't rollback - form extraction was successful
            
            # Extract attached documents from PDF pages after form pages
            # Only if we have a profile and the file is a PDF
            if profile and file_path.lower().endswith('.pdf'):
                try:
                    from backend.utils.document_extractor import extract_supporting_documents, FORM_PAGE_COUNT
                    from backend.utils.file_handler import load_all_pdf_pages
                    
                    # Load all pages to check total count
                    all_pages = load_all_pdf_pages(file_path)
                    total_pages = len(all_pages)
                    
                    # Extract pages from FORM_PAGE_COUNT onwards as documents
                    if total_pages > FORM_PAGE_COUNT:
                        logger.info(f"Extracting supporting documents from PDF (pages {FORM_PAGE_COUNT + 1}-{total_pages})")
                        
                        # Use the unified extraction function
                        extract_supporting_documents(
                            pdf_images=all_pages[FORM_PAGE_COUNT:],
                            form_id=form.id,
                            student_name=form.student_name,
                            du_portal_number=form.du_portal_form_number,
                            db=local_db,
                            upload_dir=Path(settings.UPLOAD_DIR).resolve(),
                            page_offset=FORM_PAGE_COUNT
                        )
                        # Note: extract_supporting_documents handles its own DB commit for documents
                            
                except Exception as doc_extraction_error:
                    # Log but don't fail the batch upload if document extraction fails
                    logger.warning(f"Failed to extract documents from form {form.id}: {doc_extraction_error}", exc_info=True)
            
            form_id = form.id
            
            return {
                "filename": original_filename or filename,
                "form_id": form_id,
                "status": "success",
                "confidence": ocr_result.get("confidence", 0)
            }
            
        except Exception as e:
            import traceback
            error_msg = str(e)
            error_trace = traceback.format_exc()
            logger.error(f"Batch upload error for {file_info.get('original_filename', 'unknown')}: {error_msg}\n{error_trace}")
            return {
                "filename": file_info.get("original_filename", "unknown"),
                "status": "error",
                "error": error_msg
            }
        finally:
            local_db.close()
    
    # Start batch processing with saved file info
    logger.info(f"Starting batch processing for {len(saved_files)} files with provider {provider_name}")
    
    # Create job first
    import uuid
    from datetime import datetime
    job_id = str(uuid.uuid4())
    
    # Create the job object
    job = BatchJob(
        job_id=job_id,
        status=JobStatus.PENDING,
        total_items=len(saved_files),
        processed_items=0,
        successful_items=0,
        failed_items=0,
        created_at=datetime.utcnow()
    )
    batch_processor.jobs[job_id] = job
    
    # Use BackgroundTasks to ensure execution
    async def run_batch_processing():
        """Wrapper to run batch processing in background"""
        try:
            logger.info(f"Background task started for job {job_id} with {len(saved_files)} files")
            await batch_processor._process_items(job, saved_files, process_form)
            logger.info(f"Background task completed for job {job_id}")
        except Exception as e:
            logger.error(f"Background task failed for job {job_id}: {e}", exc_info=True)
            job.status = JobStatus.FAILED
            job.completed_at = datetime.utcnow()
    
    # Add to background tasks - this ensures it runs after response is sent
    background_tasks.add_task(run_batch_processing)
    logger.info(f"Batch job {job_id} created, processing {len(saved_files)} files")
    
    return {
        "job_id": job_id,
        "total_files": len(files),
        "status": "processing",
        "message": f"Batch upload started. Use /api/batch-upload/{job_id}/status to check progress"
    }

@router.get("/batch-upload/{job_id}/status")
async def get_batch_job_status(job_id: str, user: CurrentUser = Depends(RequireStaffOrAdmin)):
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
async def get_batch_job_results(
    job_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    user: CurrentUser = Depends(RequireStaffOrAdmin),
):
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
async def cancel_batch_job(job_id: str, user: CurrentUser = Depends(RequireStaffOrAdmin)):
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
    limit: int = Query(20, ge=1, le=100),
    user: CurrentUser = Depends(RequireStaffOrAdmin),
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
