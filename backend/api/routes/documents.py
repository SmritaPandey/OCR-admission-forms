from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query, Form, Response
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import Optional, List, Dict, Any
from datetime import datetime
from backend.database import get_db, StudentDocument, AdmissionForm, StudentProfile, DocumentCategory
from backend.models.document import DocumentResponse, DocumentDetailResponse
from backend.utils.file_handler import save_document_file
from backend.utils.document_manager import document_manager
from backend.config import settings
from backend.api.dependencies import RequireAnyAuth, RequireStaffOrAdmin
from backend.models.auth_models import CurrentUser
from pathlib import Path
import os

router = APIRouter()

@router.post("/upload", response_model=DocumentResponse, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    document_category: str = Form(...),
    description: Optional[str] = Form(None),
    form_id: Optional[int] = Form(None),
    student_profile_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(RequireStaffOrAdmin),
):
    """
    Upload a document and attach it to either a form or student profile.
    At least one of form_id or student_profile_id must be provided.
    """
    # Validate category
    try:
        category = DocumentCategory(document_category)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid document category. Must be one of: {[c.value for c in DocumentCategory]}"
        )
    
    # Validate that at least one link is provided
    if not form_id and not student_profile_id:
        raise HTTPException(
            status_code=400,
            detail="Either form_id or student_profile_id must be provided"
        )
    
    # Validate form_id if provided
    if form_id:
        form = db.query(AdmissionForm).filter(AdmissionForm.id == form_id).first()
        if not form:
            raise HTTPException(status_code=404, detail="Form not found")
    
    # Validate student_profile_id if provided
    if student_profile_id:
        profile = db.query(StudentProfile).filter(StudentProfile.id == student_profile_id).first()
        if not profile:
            raise HTTPException(status_code=404, detail="Student profile not found")
    
    try:
        # Save file
        file_path, relative_path, file_size = await save_document_file(file)
        
        # Create document record
        document = StudentDocument(
            filename=file.filename or relative_path,
            file_path=relative_path,
            document_category=category,
            description=description,
            file_size=file_size,
            form_id=form_id,
            student_profile_id=student_profile_id
        )
        db.add(document)
        db.commit()
        db.refresh(document)
        
        return DocumentResponse.model_validate(document)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


# Moved routes above /{document_id} to prevent shadowing
# IMPORTANT: These routes must come before /{document_id} route to avoid path conflicts

@router.get("/forms/{form_id}/documents", response_model=List[DocumentResponse], tags=["documents"])
async def get_form_documents(
    form_id: int, db: Session = Depends(get_db),
    user: CurrentUser = Depends(RequireAnyAuth),
):
    """Get all documents for a specific form"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Getting documents for form_id: {form_id}")
    
    try:
        form = db.query(AdmissionForm).filter(AdmissionForm.id == form_id).first()
        if not form:
            logger.warning(f"Form {form_id} not found")
            raise HTTPException(status_code=404, detail="Form not found")
        
        documents = db.query(StudentDocument).filter(
            StudentDocument.form_id == form_id
        ).order_by(StudentDocument.upload_date.desc()).all()
        
        logger.info(f"Found {len(documents)} documents for form {form_id}")
        return [DocumentResponse.model_validate(doc) for doc in documents]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading documents for form {form_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to load documents: {str(e)}")

@router.get("/students/{profile_id}/documents", response_model=List[DocumentResponse], tags=["documents"])
async def get_student_documents(
    profile_id: int, db: Session = Depends(get_db),
    user: CurrentUser = Depends(RequireAnyAuth),
):
    """Get all documents for a specific student profile"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Getting documents for student_profile_id: {profile_id}")
    
    try:
        profile = db.query(StudentProfile).filter(StudentProfile.id == profile_id).first()
        if not profile:
            logger.warning(f"Student profile {profile_id} not found")
            raise HTTPException(status_code=404, detail="Student profile not found")
        
        documents = db.query(StudentDocument).filter(
            StudentDocument.student_profile_id == profile_id
        ).order_by(StudentDocument.upload_date.desc()).all()
        
        logger.info(f"Found {len(documents)} documents for student profile {profile_id}")
        return [DocumentResponse.model_validate(doc) for doc in documents]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading documents for student profile {profile_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to load documents: {str(e)}")

@router.get("/search/results", response_model=List[DocumentResponse])
async def search_documents(
    document_category: Optional[str] = Query(None),
    student_name: Optional[str] = Query(None),
    form_id: Optional[int] = Query(None),
    student_profile_id: Optional[int] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=1000),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(RequireAnyAuth),
):
    """Search documents by various criteria"""
    query = db.query(StudentDocument)
    
    # Build filters
    filters = []
    if document_category:
        try:
            category = DocumentCategory(document_category)
            filters.append(StudentDocument.document_category == category)
        except ValueError:
            pass  # Ignore invalid category
    
    if form_id:
        filters.append(StudentDocument.form_id == form_id)
    
    if student_profile_id:
        filters.append(StudentDocument.student_profile_id == student_profile_id)
    
    if student_name:
        # Join with student profiles to search by name
        query = query.join(StudentProfile, StudentDocument.student_profile_id == StudentProfile.id)
        filters.append(StudentProfile.student_name.ilike(f"%{student_name}%"))
    
    if date_from:
        try:
            from datetime import datetime
            date_from_obj = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
            filters.append(StudentDocument.upload_date >= date_from_obj)
        except:
            pass
    
    if date_to:
        try:
            from datetime import datetime
            date_to_obj = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
            filters.append(StudentDocument.upload_date <= date_to_obj)
        except:
            pass
    
    if filters:
        query = query.filter(and_(*filters))
    
    documents = query.order_by(StudentDocument.upload_date.desc()).all()
    
    return [DocumentResponse.model_validate(doc) for doc in documents]

@router.get("/categories/list")
async def get_document_categories(user: CurrentUser = Depends(RequireAnyAuth)):
    """Get list of available document categories"""
    return {
        "categories": [{"value": cat.value, "name": cat.value} for cat in DocumentCategory]
    }

# IMPORTANT: This route must come AFTER all specific routes like /forms/{form_id}/documents
# to avoid path conflicts. FastAPI matches routes in order.
@router.get("/{document_id}", response_model=DocumentDetailResponse)
async def get_document(
    document_id: int, db: Session = Depends(get_db),
    user: CurrentUser = Depends(RequireAnyAuth),
):
    """Get detailed information about a specific document"""
    document = db.query(StudentDocument).filter(StudentDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentDetailResponse.model_validate(document)

@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: int, db: Session = Depends(get_db),
    user: CurrentUser = Depends(RequireStaffOrAdmin),
):
    """Delete a document and its associated file"""
    document = db.query(StudentDocument).filter(StudentDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Delete file if it exists
    upload_dir = Path(settings.UPLOAD_DIR).resolve()
    full_file_path = upload_dir / document.file_path
    if full_file_path.exists():
        try:
            os.remove(full_file_path)
        except Exception as e:
            print(f"Warning: Could not delete file {full_file_path}: {e}")
    
    db.delete(document)
    db.commit()
    return None


# /categories/list moved up

@router.get("/{document_id}/download")
async def download_document(
    document_id: int, db: Session = Depends(get_db),
    user: CurrentUser = Depends(RequireAnyAuth),
):
    """Download a document file"""
    document = db.query(StudentDocument).filter(StudentDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    upload_dir = Path(settings.UPLOAD_DIR).resolve()
    file_path = upload_dir / document.file_path
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Document file not found")
    
    return FileResponse(
        path=str(file_path),
        filename=document.filename,
        media_type="application/octet-stream"
    )

@router.get("/{document_id}/preview")
async def preview_document(
    document_id: int, db: Session = Depends(get_db),
    user: CurrentUser = Depends(RequireAnyAuth),
):
    """Preview a document (for images/PDFs)"""
    document = db.query(StudentDocument).filter(StudentDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    upload_dir = Path(settings.UPLOAD_DIR).resolve()
    file_path = upload_dir / document.file_path
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Document file not found")
    
    # Determine media type based on extension
    ext = file_path.suffix.lower()
    media_types = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.pdf': 'application/pdf',
        '.gif': 'image/gif',
        '.bmp': 'image/bmp',
        '.tiff': 'image/tiff'
    }
    
    media_type = media_types.get(ext, 'application/octet-stream')
    
    return FileResponse(
        path=str(file_path),
        media_type=media_type
    )

@router.post("/bulk-upload", response_model=List[DocumentResponse], status_code=201)
async def bulk_upload_documents(
    files: List[UploadFile] = File(...),
    document_category: str = Form(...),
    student_profile_id: Optional[int] = Form(None),
    form_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(RequireStaffOrAdmin),
):
    """Upload multiple documents at once"""
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    # Validate category
    try:
        category = DocumentCategory(document_category)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid document category. Must be one of: {[c.value for c in DocumentCategory]}"
        )
    
    # Validate that at least one link is provided
    if not form_id and not student_profile_id:
        raise HTTPException(
            status_code=400,
            detail="Either form_id or student_profile_id must be provided"
        )
    
    # Validate form_id if provided
    if form_id:
        form = db.query(AdmissionForm).filter(AdmissionForm.id == form_id).first()
        if not form:
            raise HTTPException(status_code=404, detail="Form not found")
    
    # Validate student_profile_id if provided
    if student_profile_id:
        profile = db.query(StudentProfile).filter(StudentProfile.id == student_profile_id).first()
        if not profile:
            raise HTTPException(status_code=404, detail="Student profile not found")
    
    uploaded_documents = []
    errors = []
    
    for file in files:
        try:
            # Save file
            file_path, relative_path, file_size = await save_document_file(file)
            
            # Create document record
            document = StudentDocument(
                filename=file.filename or relative_path,
                file_path=relative_path,
                document_category=category,
                file_size=file_size,
                form_id=form_id,
                student_profile_id=student_profile_id
            )
            db.add(document)
            db.flush()  # Flush to get ID but don't commit yet
            uploaded_documents.append(document)
            
        except Exception as e:
            errors.append({"filename": file.filename, "error": str(e)})
            continue
    
    # Commit all successful uploads
    if uploaded_documents:
        db.commit()
        for doc in uploaded_documents:
            db.refresh(doc)
    
    if errors and not uploaded_documents:
        raise HTTPException(status_code=400, detail=f"All uploads failed: {errors}")
    
    response = [DocumentResponse.model_validate(doc) for doc in uploaded_documents]
    
    if errors:
        # Return partial success with errors
        return response  # Could include errors in response if needed
    
    return response

# --- Export Related Logic ---

DOCUMENT_EXPORT_FIELDS = [
    ("id", "Document ID"),
    ("filename", "Filename"),
    ("document_category", "Category"),
    ("description", "Description"),
    ("file_size", "File Size (Bytes)"),
    ("upload_date", "Upload Date"),
    ("form_id", "Form ID"),
    ("student_profile_id", "Student Profile ID"),
    ("file_path", "File Path"),
]

def document_to_csv_row(doc: StudentDocument) -> List[str]:
    row = []
    for attr, _ in DOCUMENT_EXPORT_FIELDS:
        value = getattr(doc, attr, None)
        if isinstance(value, datetime):
            value = value.isoformat()
        elif hasattr(value, 'value'): # For Enums
            value = value.value
        elif value is None:
            value = ""
        row.append(str(value))
    return row

def document_to_json_dict(doc: StudentDocument) -> Dict[str, Any]:
    record = {}
    for attr, _ in DOCUMENT_EXPORT_FIELDS:
        value = getattr(doc, attr, None)
        if isinstance(value, datetime):
            record[attr] = value.isoformat()
        elif hasattr(value, 'value'): # For Enums
            record[attr] = value.value
        else:
            record[attr] = value
    return record

@router.get("/export")
async def export_documents(
    format: str = Query("csv", regex="^(csv|json|excel|pdf)$"),
    document_category: Optional[str] = Query(None),
    student_name: Optional[str] = Query(None),
    form_id: Optional[int] = Query(None),
    student_profile_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(RequireStaffOrAdmin),
):
    """Export documents to CSV, JSON, Excel or PDF"""
    import io
    import csv
    import json
    from datetime import datetime
    import pandas as pd
    
    query = db.query(StudentDocument)
    
    # Build filters (reuse logic from search_documents if possible, but distinct here for simplicity)
    filters = []
    if document_category:
        try:
            category = DocumentCategory(document_category)
            filters.append(StudentDocument.document_category == category)
        except ValueError:
            pass
    
    if form_id:
        filters.append(StudentDocument.form_id == form_id)
    
    if student_profile_id:
        filters.append(StudentDocument.student_profile_id == student_profile_id)
    
    if student_name:
        query = query.join(StudentProfile, StudentDocument.student_profile_id == StudentProfile.id)
        filters.append(StudentProfile.student_name.ilike(f"%{student_name}%"))
    
    if filters:
        query = query.filter(and_(*filters))
    
    documents = query.order_by(StudentDocument.upload_date.desc()).all()
    
    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([header for _, header in DOCUMENT_EXPORT_FIELDS])
        for doc in documents:
            writer.writerow(document_to_csv_row(doc))
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=documents_export.csv"}
        )
    
    elif format == "json":
        data = [document_to_json_dict(doc) for doc in documents]
        return Response(
            content=json.dumps(data, indent=2, default=str),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=documents_export.json"}
        )
    
    elif format == "excel":
        data = [document_to_json_dict(doc) for doc in documents]
        df = pd.DataFrame(data)
        header_map = {attr: header for attr, header in DOCUMENT_EXPORT_FIELDS}
        df = df.rename(columns=header_map)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Documents', index=False)
        output.seek(0)
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=documents_export.xlsx"}
        )
    
    elif format == "pdf":
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.enums import TA_CENTER
            
            output = io.BytesIO()
            doc = SimpleDocTemplate(output, pagesize=landscape(A4))
            styles = getSampleStyleSheet()
            elements = [Paragraph("Documents Export", styles['Heading1']), Spacer(1, 12)]
            
            table_data = [[header for _, header in DOCUMENT_EXPORT_FIELDS[:7]]] # Only first 7 fields for PDF
            for doc_obj in documents:
                row = []
                for attr, _ in DOCUMENT_EXPORT_FIELDS[:7]:
                    val = getattr(doc_obj, attr, "")
                    if isinstance(val, datetime): val = val.strftime("%Y-%m-%d")
                    elif hasattr(val, 'value'): val = val.value
                    row.append(str(val) if val is not None else "-")
                table_data.append(row)
                
            t = Table(table_data)
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.navy),
                ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey)
            ]))
            elements.append(t)
            doc.build(elements)
            output.seek(0)
            return StreamingResponse(
                output,
                media_type="application/pdf",
                headers={"Content-Disposition": "attachment; filename=documents_export.pdf"}
            )
        except ImportError:
            raise HTTPException(status_code=500, detail="PDF export requires reportlab library")

    return {"message": "Export format not supported"}

