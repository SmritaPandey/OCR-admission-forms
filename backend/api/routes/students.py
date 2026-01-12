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
    roll_number: Optional[str]
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
    aadhar_number: Optional[str] = None,
    roll_number: Optional[str] = None
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
            aadhar_number=aadhar_number,
            roll_number=roll_number
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
    else:
        # Update timestamp and roll_number if provided
        profile.updated_date = datetime.utcnow()
        if roll_number and not profile.roll_number:
            profile.roll_number = roll_number
        db.commit()
    
    return profile

@router.get("/", response_model=List[StudentProfileResponse])
async def list_student_profiles(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),  # Increased default limit
    student_name: Optional[str] = Query(None),
    roll_number: Optional[str] = Query(None),
    aadhar_number: Optional[str] = Query(None),
    # Advanced search filters from form fields
    phone_number: Optional[str] = Query(None),
    email: Optional[str] = Query(None),
    enrollment_number: Optional[str] = Query(None),
    application_number: Optional[str] = Query(None),
    course_applied: Optional[str] = Query(None),
    gender: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    father_name: Optional[str] = Query(None),
    mother_name: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    pincode: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """List all student profiles with search capability including form fields"""
    query = db.query(StudentProfile)
    
    # Build filters on StudentProfile
    profile_filters = []
    if student_name:
        profile_filters.append(StudentProfile.student_name.ilike(f"%{student_name}%"))
    if roll_number:
        profile_filters.append(StudentProfile.roll_number.ilike(f"%{roll_number}%"))
    if aadhar_number:
        profile_filters.append(StudentProfile.aadhar_number.ilike(f"%{aadhar_number}%"))
    
    # If advanced filters are provided, join with AdmissionForm and filter
    has_form_filters = any([
        phone_number, email, enrollment_number, application_number, course_applied,
        gender, category, father_name, mother_name, city, state, pincode
    ])
    
    if has_form_filters:
        query = query.join(AdmissionForm, StudentProfile.id == AdmissionForm.student_profile_id)
        
        form_filters = []
        if phone_number:
            form_filters.append(AdmissionForm.phone_number.ilike(f"%{phone_number}%"))
        if email:
            form_filters.append(AdmissionForm.email.ilike(f"%{email}%"))
        if enrollment_number:
            form_filters.append(AdmissionForm.enrollment_number.ilike(f"%{enrollment_number}%"))
        if application_number:
            form_filters.append(AdmissionForm.application_number.ilike(f"%{application_number}%"))
        if course_applied:
            form_filters.append(AdmissionForm.course_applied.ilike(f"%{course_applied}%"))
        if gender:
            form_filters.append(AdmissionForm.gender.ilike(f"%{gender}%"))
        if category:
            form_filters.append(AdmissionForm.category.ilike(f"%{category}%"))
        if father_name:
            form_filters.append(AdmissionForm.father_name.ilike(f"%{father_name}%"))
        if mother_name:
            form_filters.append(AdmissionForm.mother_name.ilike(f"%{mother_name}%"))
        if city:
            form_filters.append(AdmissionForm.city.ilike(f"%{city}%"))
        if state:
            form_filters.append(AdmissionForm.state.ilike(f"%{state}%"))
        if pincode:
            form_filters.append(AdmissionForm.pincode.ilike(f"%{pincode}%"))
        
        if form_filters:
            query = query.filter(and_(*form_filters))
        
        # Use distinct to avoid duplicate profiles
        query = query.distinct()
    
    if profile_filters:
        query = query.filter(and_(*profile_filters))
    
    # Order by updated date descending (most recent first)
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

class StudentProfileUpdate(BaseModel):
    student_name: Optional[str] = None
    aadhar_number: Optional[str] = None
    roll_number: Optional[str] = None

@router.patch("/{profile_id}", response_model=StudentProfileResponse)
async def update_student_profile(
    profile_id: int,
    update_data: StudentProfileUpdate,
    db: Session = Depends(get_db)
):
    """Update a student profile"""
    profile = db.query(StudentProfile).filter(StudentProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Student profile not found")
    
    # Update fields if provided
    if update_data.student_name is not None:
        profile.student_name = update_data.student_name
    if update_data.aadhar_number is not None:
        profile.aadhar_number = update_data.aadhar_number
    if update_data.roll_number is not None:
        profile.roll_number = update_data.roll_number
    
    profile.updated_date = datetime.utcnow()
    db.commit()
    db.refresh(profile)
    
    # Add counts
    profile_data = StudentProfileResponse.model_validate(profile)
    profile_data.forms_count = db.query(AdmissionForm).filter(
        AdmissionForm.student_profile_id == profile.id
    ).count()
    profile_data.documents_count = db.query(StudentDocument).filter(
        StudentDocument.student_profile_id == profile.id
    ).count()
    
    return profile_data

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
    roll_number: Optional[str] = Query(None),
    aadhar_number: Optional[str] = Query(None),
    # Advanced search filters from form fields
    phone_number: Optional[str] = Query(None),
    email: Optional[str] = Query(None),
    enrollment_number: Optional[str] = Query(None),
    application_number: Optional[str] = Query(None),
    course_applied: Optional[str] = Query(None),
    gender: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    father_name: Optional[str] = Query(None),
    mother_name: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    pincode: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=1000),  # Increased default limit
    db: Session = Depends(get_db)
):
    """Search student profiles by various criteria including form fields"""
    query = db.query(StudentProfile)
    
    # Build filters on StudentProfile
    profile_filters = []
    if student_name:
        profile_filters.append(StudentProfile.student_name.ilike(f"%{student_name}%"))
    if roll_number:
        profile_filters.append(StudentProfile.roll_number.ilike(f"%{roll_number}%"))
    if aadhar_number:
        profile_filters.append(StudentProfile.aadhar_number.ilike(f"%{aadhar_number}%"))
    
    # If advanced filters are provided, join with AdmissionForm and filter
    has_form_filters = any([
        phone_number, email, enrollment_number, application_number, course_applied,
        gender, category, father_name, mother_name, city, state, pincode
    ])
    
    if has_form_filters:
        query = query.join(AdmissionForm, StudentProfile.id == AdmissionForm.student_profile_id)
        
        form_filters = []
        if phone_number:
            form_filters.append(AdmissionForm.phone_number.ilike(f"%{phone_number}%"))
        if email:
            form_filters.append(AdmissionForm.email.ilike(f"%{email}%"))
        if enrollment_number:
            form_filters.append(AdmissionForm.enrollment_number.ilike(f"%{enrollment_number}%"))
        if application_number:
            form_filters.append(AdmissionForm.application_number.ilike(f"%{application_number}%"))
        if course_applied:
            form_filters.append(AdmissionForm.course_applied.ilike(f"%{course_applied}%"))
        if gender:
            form_filters.append(AdmissionForm.gender.ilike(f"%{gender}%"))
        if category:
            form_filters.append(AdmissionForm.category.ilike(f"%{category}%"))
        if father_name:
            form_filters.append(AdmissionForm.father_name.ilike(f"%{father_name}%"))
        if mother_name:
            form_filters.append(AdmissionForm.mother_name.ilike(f"%{mother_name}%"))
        if city:
            form_filters.append(AdmissionForm.city.ilike(f"%{city}%"))
        if state:
            form_filters.append(AdmissionForm.state.ilike(f"%{state}%"))
        if pincode:
            form_filters.append(AdmissionForm.pincode.ilike(f"%{pincode}%"))
        
        if form_filters:
            query = query.filter(and_(*form_filters))
        
        # Use distinct to avoid duplicate profiles
        query = query.distinct()
    
    if profile_filters:
        query = query.filter(and_(*profile_filters))
    
    # Pagination
    skip = (page - 1) * limit
    # Order by updated date descending (most recent first)
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


@router.delete("/{profile_id}", status_code=204)
async def delete_student_profile(
    profile_id: int,
    force: bool = Query(False, description="Force delete even if related data exists (always true for this implementation)"),
    db: Session = Depends(get_db)
):
    """
    Delete a student profile and all associated data (forms, documents, files).
    This performs a cascading delete:
    1. Deletes all associated documents and their physical files
    2. Deletes all associated forms and their physical files
    3. Deletes the student profile
    """
    profile = db.query(StudentProfile).filter(StudentProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Student profile not found")
    
    import os
    from pathlib import Path
    from backend.models.form import FormStatus
    from backend.config import settings
    
    upload_dir = Path(settings.UPLOAD_DIR).resolve()
    
    # 1. Delete all associated documents
    documents = db.query(StudentDocument).filter(
        StudentDocument.student_profile_id == profile_id
    ).all()
    
    for doc in documents:
        # Delete physical file
        try:
            full_file_path = upload_dir / doc.file_path
            if full_file_path.exists():
                os.remove(full_file_path)
            # Also try deleting thumbnail/preview if exists (optional cleanup)
        except Exception as e:
            # Log error but continue
            print(f"Error deleting document file {doc.file_path}: {e}")
            pass
        
        db.delete(doc)
    
    # 2. Delete all associated forms
    forms = db.query(AdmissionForm).filter(
        AdmissionForm.student_profile_id == profile_id
    ).all()
    
    for form in forms:
        # Delete documents associated with this form but NOT linked to student (if any)
        # (Though usually documents are linked to student, some might be just form-linked)
        form_docs = db.query(StudentDocument).filter(
            StudentDocument.form_id == form.id,
            StudentDocument.student_profile_id == None # Only those not already deleted above
        ).all()
        
        for fdoc in form_docs:
            try:
                full_file_path = upload_dir / fdoc.file_path
                if full_file_path.exists():
                    os.remove(full_file_path)
            except Exception as e:
                print(f"Error deleting form document file {fdoc.file_path}: {e}")
                pass
            db.delete(fdoc)
            
        # Delete form physical file
        try:
            full_file_path = upload_dir / form.file_path
            if full_file_path.exists():
                os.remove(full_file_path)
        except Exception as e:
            print(f"Error deleting form file {form.file_path}: {e}")
            pass
            
        db.delete(form)
    
    # 3. Delete the profile itself
    db.delete(profile)
    db.commit()
    return None
