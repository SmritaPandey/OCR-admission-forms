from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import Optional, List
from backend.database import get_db, StudentProfile, AdmissionForm, StudentDocument
from datetime import datetime
from pydantic import BaseModel

router = APIRouter()

class StudentProfileResponse(BaseModel):
    id: int
    student_name: str
    aadhar_number: Optional[str]
    created_date: datetime
    updated_date: datetime
    forms_count: int = 0
    documents_count: int = 0
    
    class Config:
        from_attributes = True

class StudentProfileDetailResponse(StudentProfileResponse):
    forms: List = []
    documents: List = []

def get_or_create_student_profile(
    db: Session,
    student_name: str,
    aadhar_number: Optional[str] = None
) -> StudentProfile:
    """
    Get existing student profile or create a new one.
    Uses student_name + aadhar_number as composite identifier.
    """
    if not student_name:
        raise ValueError("Student name is required")
    
    # Try to find existing profile
    query = db.query(StudentProfile).filter(StudentProfile.student_name == student_name)
    if aadhar_number:
        query = query.filter(StudentProfile.aadhar_number == aadhar_number)
    else:
        # If no aadhar, match only by name (less reliable)
        query = query.filter(StudentProfile.aadhar_number.is_(None))
    
    profile = query.first()
    
    if not profile:
        # Create new profile
        profile = StudentProfile(
            student_name=student_name,
            aadhar_number=aadhar_number
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
    else:
        # Update timestamp
        profile.updated_date = datetime.utcnow()
        db.commit()
    
    return profile

@router.get("/", response_model=List[StudentProfileResponse])
async def list_student_profiles(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    student_name: Optional[str] = Query(None),
    aadhar_number: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """List all student profiles with search capability"""
    query = db.query(StudentProfile)
    
    # Build filters
    filters = []
    if student_name:
        filters.append(StudentProfile.student_name.ilike(f"%{student_name}%"))
    if aadhar_number:
        filters.append(StudentProfile.aadhar_number.ilike(f"%{aadhar_number}%"))
    
    if filters:
        query = query.filter(and_(*filters))
    
    profiles = query.order_by(StudentProfile.updated_date.desc()).offset(skip).limit(limit).all()
    
    # Add counts
    result = []
    for profile in profiles:
        profile_data = StudentProfileResponse.model_validate(profile)
        profile_data.forms_count = db.query(AdmissionForm).filter(
            AdmissionForm.student_profile_id == profile.id
        ).count()
        profile_data.documents_count = db.query(StudentDocument).filter(
            StudentDocument.student_profile_id == profile.id
        ).count()
        result.append(profile_data)
    
    return result

@router.get("/{profile_id}", response_model=StudentProfileDetailResponse)
async def get_student_profile(profile_id: int, db: Session = Depends(get_db)):
    """Get detailed information about a student profile with all forms and documents"""
    profile = db.query(StudentProfile).filter(StudentProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Student profile not found")
    
    # Get all forms for this student
    forms = db.query(AdmissionForm).filter(
        AdmissionForm.student_profile_id == profile_id
    ).order_by(AdmissionForm.upload_date.desc()).all()
    
    # Get all documents for this student
    documents = db.query(StudentDocument).filter(
        StudentDocument.student_profile_id == profile_id
    ).order_by(StudentDocument.upload_date.desc()).all()
    
    # Build response
    from backend.models.form import FormDetailResponse
    from backend.models.document import DocumentResponse
    
    profile_data = StudentProfileDetailResponse.model_validate(profile)
    profile_data.forms = [FormDetailResponse.model_validate(form) for form in forms]
    profile_data.documents = [DocumentResponse.model_validate(doc) for doc in documents]
    profile_data.forms_count = len(forms)
    profile_data.documents_count = len(documents)
    
    return profile_data

@router.post("/", response_model=StudentProfileResponse, status_code=201)
async def create_student_profile(
    student_name: str,
    aadhar_number: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Create a new student profile manually"""
    if not student_name:
        raise HTTPException(status_code=400, detail="Student name is required")
    
    # Check if profile already exists
    existing = db.query(StudentProfile).filter(
        StudentProfile.student_name == student_name
    )
    if aadhar_number:
        existing = existing.filter(StudentProfile.aadhar_number == aadhar_number)
    else:
        existing = existing.filter(StudentProfile.aadhar_number.is_(None))
    
    if existing.first():
        raise HTTPException(status_code=400, detail="Student profile already exists")
    
    profile = StudentProfile(
        student_name=student_name,
        aadhar_number=aadhar_number
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    
    return StudentProfileResponse.model_validate(profile)

@router.get("/{profile_id}/forms", response_model=List)
async def get_student_forms(profile_id: int, db: Session = Depends(get_db)):
    """Get all forms for a student profile"""
    profile = db.query(StudentProfile).filter(StudentProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Student profile not found")
    
    forms = db.query(AdmissionForm).filter(
        AdmissionForm.student_profile_id == profile_id
    ).order_by(AdmissionForm.upload_date.desc()).all()
    
    from backend.models.form import FormDetailResponse
    return [FormDetailResponse.model_validate(form) for form in forms]

@router.get("/search/results", response_model=List[StudentProfileResponse])
async def search_student_profiles(
    student_name: Optional[str] = Query(None),
    aadhar_number: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Search student profiles by various criteria"""
    query = db.query(StudentProfile)
    
    # Build filters
    filters = []
    if student_name:
        filters.append(StudentProfile.student_name.ilike(f"%{student_name}%"))
    if aadhar_number:
        filters.append(StudentProfile.aadhar_number.ilike(f"%{aadhar_number}%"))
    
    if filters:
        query = query.filter(and_(*filters))
    
    # Pagination
    skip = (page - 1) * limit
    profiles = query.order_by(StudentProfile.updated_date.desc()).offset(skip).limit(limit).all()
    
    # Add counts
    result = []
    for profile in profiles:
        profile_data = StudentProfileResponse.model_validate(profile)
        profile_data.forms_count = db.query(AdmissionForm).filter(
            AdmissionForm.student_profile_id == profile.id
        ).count()
        profile_data.documents_count = db.query(StudentDocument).filter(
            StudentDocument.student_profile_id == profile.id
        ).count()
        result.append(profile_data)
    
    return result

