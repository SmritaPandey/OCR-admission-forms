from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query, Form
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import Optional, List
from backend.database import get_db, StudentDocument, AdmissionForm, StudentProfile, DocumentCategory
from backend.models.document import DocumentResponse, DocumentDetailResponse
from backend.utils.file_handler import save_document_file
from backend.config import settings
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
    db: Session = Depends(get_db)
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

@router.get("/{document_id}", response_model=DocumentDetailResponse)
async def get_document(document_id: int, db: Session = Depends(get_db)):
    """Get detailed information about a specific document"""
    document = db.query(StudentDocument).filter(StudentDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentDetailResponse.model_validate(document)

@router.get("/forms/{form_id}/documents", response_model=List[DocumentResponse])
async def get_form_documents(form_id: int, db: Session = Depends(get_db)):
    """Get all documents attached to a specific form"""
    form = db.query(AdmissionForm).filter(AdmissionForm.id == form_id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    
    documents = db.query(StudentDocument).filter(
        StudentDocument.form_id == form_id
    ).order_by(StudentDocument.upload_date.desc()).all()
    
    return [DocumentResponse.model_validate(doc) for doc in documents]

@router.get("/students/{profile_id}/documents", response_model=List[DocumentResponse])
async def get_student_documents(profile_id: int, db: Session = Depends(get_db)):
    """Get all documents attached to a student profile"""
    profile = db.query(StudentProfile).filter(StudentProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Student profile not found")
    
    documents = db.query(StudentDocument).filter(
        StudentDocument.student_profile_id == profile_id
    ).order_by(StudentDocument.upload_date.desc()).all()
    
    return [DocumentResponse.model_validate(doc) for doc in documents]

@router.get("/search/results", response_model=List[DocumentResponse])
async def search_documents(
    document_category: Optional[str] = Query(None),
    student_name: Optional[str] = Query(None),
    form_id: Optional[int] = Query(None),
    student_profile_id: Optional[int] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
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
    
    # Pagination
    skip = (page - 1) * limit
    documents = query.order_by(StudentDocument.upload_date.desc()).offset(skip).limit(limit).all()
    
    return [DocumentResponse.model_validate(doc) for doc in documents]

@router.delete("/{document_id}", status_code=204)
async def delete_document(document_id: int, db: Session = Depends(get_db)):
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

@router.get("/categories/list")
async def get_document_categories():
    """Get list of available document categories"""
    return {
        "categories": [{"value": cat.value, "name": cat.value} for cat in DocumentCategory]
    }

