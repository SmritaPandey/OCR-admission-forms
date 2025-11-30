from __future__ import annotations

from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any, List
from backend.database import FormStatus

class FormBase(BaseModel):
    filename: str
    ocr_provider: str

class FormCreate(FormBase):
    pass

class FormResponse(FormBase):
    id: int
    upload_date: datetime
    status: FormStatus
    file_path: str
    
    class Config:
        from_attributes = True

class PageExtraction(BaseModel):
    page: int
    raw_text: str = ""
    confidence: Optional[float] = None
    provider: Optional[str] = None


class ExtractedData(BaseModel):
    raw_text: str = ""
    confidence: Optional[float] = None
    structured_data: Optional[Dict[str, Any]] = None
    provider: Optional[str] = None
    word_count: Optional[int] = None
    psm_mode: Optional[int] = None
    pages_processed: Optional[int] = None
    page_results: Optional[List[PageExtraction]] = None

class StudentInfo(BaseModel):
    # Basic Details
    student_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    category: Optional[str] = None
    nationality: Optional[str] = None
    religion: Optional[str] = None
    aadhar_number: Optional[str] = None
    blood_group: Optional[str] = None
    
    # Address Details
    permanent_address: Optional[str] = None
    correspondence_address: Optional[str] = None
    pincode: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    
    # Contact Details
    phone_number: Optional[str] = None
    alternate_phone: Optional[str] = None
    email: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    
    # Guardian/Parent Details
    father_name: Optional[str] = None
    father_occupation: Optional[str] = None
    father_phone: Optional[str] = None
    mother_name: Optional[str] = None
    mother_occupation: Optional[str] = None
    mother_phone: Optional[str] = None
    guardian_name: Optional[str] = None
    guardian_relation: Optional[str] = None
    guardian_phone: Optional[str] = None
    annual_income: Optional[str] = None
    
    # Educational Qualifications
    tenth_board: Optional[str] = None
    tenth_year: Optional[str] = None
    tenth_percentage: Optional[str] = None
    tenth_school: Optional[str] = None
    twelfth_board: Optional[str] = None
    twelfth_year: Optional[str] = None
    twelfth_percentage: Optional[str] = None
    twelfth_school: Optional[str] = None
    previous_qualification: Optional[str] = None
    graduation_details: Optional[str] = None
    
    # Course Application Details
    course_applied: Optional[str] = None
    application_number: Optional[str] = None
    enrollment_number: Optional[str] = None
    admission_date: Optional[str] = None
    
    additional_info: Optional[Dict[str, Any]] = None

class FormVerification(BaseModel):
    # Basic Details
    student_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    category: Optional[str] = None
    nationality: Optional[str] = None
    religion: Optional[str] = None
    aadhar_number: Optional[str] = None
    blood_group: Optional[str] = None
    
    # Address Details
    permanent_address: Optional[str] = None
    correspondence_address: Optional[str] = None
    pincode: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    
    # Contact Details
    phone_number: Optional[str] = None
    alternate_phone: Optional[str] = None
    email: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    
    # Guardian/Parent Details
    father_name: Optional[str] = None
    father_occupation: Optional[str] = None
    father_phone: Optional[str] = None
    mother_name: Optional[str] = None
    mother_occupation: Optional[str] = None
    mother_phone: Optional[str] = None
    guardian_name: Optional[str] = None
    guardian_relation: Optional[str] = None
    guardian_phone: Optional[str] = None
    annual_income: Optional[str] = None
    
    # Educational Qualifications
    tenth_board: Optional[str] = None
    tenth_year: Optional[str] = None
    tenth_percentage: Optional[str] = None
    tenth_school: Optional[str] = None
    twelfth_board: Optional[str] = None
    twelfth_year: Optional[str] = None
    twelfth_percentage: Optional[str] = None
    twelfth_school: Optional[str] = None
    previous_qualification: Optional[str] = None
    graduation_details: Optional[str] = None
    
    # Course Application Details
    course_applied: Optional[str] = None
    application_number: Optional[str] = None
    enrollment_number: Optional[str] = None
    admission_date: Optional[str] = None
    
    additional_info: Optional[Dict[str, Any]] = None

class FormDetailResponse(FormResponse):
    extracted_data: Optional[ExtractedData] = None
    student_profile_id: Optional[int] = None
    documents: Optional[List["DocumentResponse"]] = None  # Populated at runtime
    
    # Basic Details
    student_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    category: Optional[str] = None
    nationality: Optional[str] = None
    religion: Optional[str] = None
    aadhar_number: Optional[str] = None
    blood_group: Optional[str] = None
    
    # Address Details
    permanent_address: Optional[str] = None
    correspondence_address: Optional[str] = None
    pincode: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    
    # Contact Details
    phone_number: Optional[str] = None
    alternate_phone: Optional[str] = None
    email: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    
    # Guardian/Parent Details
    father_name: Optional[str] = None
    father_occupation: Optional[str] = None
    father_phone: Optional[str] = None
    mother_name: Optional[str] = None
    mother_occupation: Optional[str] = None
    mother_phone: Optional[str] = None
    guardian_name: Optional[str] = None
    guardian_relation: Optional[str] = None
    guardian_phone: Optional[str] = None
    annual_income: Optional[str] = None
    
    # Educational Qualifications
    tenth_board: Optional[str] = None
    tenth_year: Optional[str] = None
    tenth_percentage: Optional[str] = None
    tenth_school: Optional[str] = None
    twelfth_board: Optional[str] = None
    twelfth_year: Optional[str] = None
    twelfth_percentage: Optional[str] = None
    twelfth_school: Optional[str] = None
    previous_qualification: Optional[str] = None
    graduation_details: Optional[str] = None
    
    # Course Application Details
    course_applied: Optional[str] = None
    application_number: Optional[str] = None
    enrollment_number: Optional[str] = None
    admission_date: Optional[str] = None
    
    additional_info: Optional[Dict[str, Any]] = None
    verified_date: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class FormSearchParams(BaseModel):
    student_name: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    course_applied: Optional[str] = None
    status: Optional[FormStatus] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    page: int = 1
    limit: int = 20


class FormExtractionResponse(BaseModel):
    message: str
    result: ExtractedData


from backend.models.document import DocumentResponse  # noqa: E402

FormDetailResponse.model_rebuild()

