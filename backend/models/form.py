from __future__ import annotations

from pydantic import BaseModel, model_validator
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
    # Name fields
    student_name: Optional[str] = None
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    surname: Optional[str] = None
    
    # Basic Personal Details
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    category: Optional[str] = None
    nationality: Optional[str] = None
    religion: Optional[str] = None
    aadhar_number: Optional[str] = None
    blood_group: Optional[str] = None
    below_poverty_line: Optional[str] = None
    minority_category: Optional[str] = None
    
    # Academic & Admission Details
    academic_session: Optional[str] = None
    course: Optional[str] = None
    admission_category: Optional[str] = None
    admission_category_other: Optional[str] = None
    du_portal_form_number: Optional[str] = None
    cuet_score: Optional[str] = None
    college_roll_no: Optional[str] = None
    date_of_admission: Optional[str] = None
    du_enrollment_number: Optional[str] = None
    hindi_medium_preference: Optional[str] = None
    
    # Address Details
    permanent_address: Optional[str] = None
    permanent_address_line1: Optional[str] = None
    permanent_address_line2: Optional[str] = None
    permanent_address_line3: Optional[str] = None
    permanent_state: Optional[str] = None
    permanent_pincode: Optional[str] = None
    correspondence_address: Optional[str] = None
    correspondence_address_line1: Optional[str] = None
    correspondence_address_line2: Optional[str] = None
    correspondence_address_line3: Optional[str] = None
    correspondence_state: Optional[str] = None
    correspondence_pincode: Optional[str] = None
    pincode: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    
    # Contact Details
    phone_number: Optional[str] = None
    alternate_phone: Optional[str] = None
    email: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    
    # Mother's Details
    mother_name: Optional[str] = None
    mother_occupation: Optional[str] = None
    mother_designation: Optional[str] = None
    mother_organization: Optional[str] = None
    mother_email: Optional[str] = None
    mother_mobile: Optional[str] = None
    mother_landline_code: Optional[str] = None
    mother_landline: Optional[str] = None
    mother_phone: Optional[str] = None
    
    # Father's Details
    father_name: Optional[str] = None
    father_occupation: Optional[str] = None
    father_designation: Optional[str] = None
    father_organization: Optional[str] = None
    father_email: Optional[str] = None
    father_mobile: Optional[str] = None
    father_landline_code: Optional[str] = None
    father_landline: Optional[str] = None
    father_phone: Optional[str] = None
    
    # Guardian Details
    guardian_name: Optional[str] = None
    guardian_relation: Optional[str] = None
    guardian_residential_address: Optional[str] = None
    guardian_organization: Optional[str] = None
    guardian_email: Optional[str] = None
    guardian_mobile: Optional[str] = None
    guardian_landline_code: Optional[str] = None
    guardian_landline: Optional[str] = None
    guardian_phone: Optional[str] = None
    
    # Family Income
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
    twelfth_roll_number: Optional[str] = None
    twelfth_institution: Optional[str] = None
    hindi_studied_upto: Optional[str] = None
    previous_qualification: Optional[str] = None
    graduation_details: Optional[str] = None
    
    # Course Application Details
    course_applied: Optional[str] = None
    application_number: Optional[str] = None
    enrollment_number: Optional[str] = None
    admission_date: Optional[str] = None
    
    # Certificate Details
    category_certificate_authority: Optional[str] = None
    category_certificate_number: Optional[str] = None
    category_certificate_date: Optional[str] = None
    disability_percentage: Optional[str] = None
    disability_type: Optional[str] = None
    udid_number: Optional[str] = None
    
    # CUET Marks
    cuet_subject_1: Optional[str] = None
    cuet_total_score_1: Optional[str] = None
    cuet_score_obtained_1: Optional[str] = None
    cuet_subject_2: Optional[str] = None
    cuet_total_score_2: Optional[str] = None
    cuet_score_obtained_2: Optional[str] = None
    cuet_subject_3: Optional[str] = None
    cuet_total_score_3: Optional[str] = None
    cuet_score_obtained_3: Optional[str] = None
    cuet_subject_4: Optional[str] = None
    cuet_total_score_4: Optional[str] = None
    cuet_score_obtained_4: Optional[str] = None
    cuet_subject_5: Optional[str] = None
    cuet_total_score_5: Optional[str] = None
    cuet_score_obtained_5: Optional[str] = None
    cuet_subject_6: Optional[str] = None
    cuet_total_score_6: Optional[str] = None
    cuet_score_obtained_6: Optional[str] = None
    
    # Extra CUET Marks (7-10) to be stored in additional_info
    cuet_subject_7: Optional[str] = None
    cuet_total_score_7: Optional[str] = None
    cuet_score_obtained_7: Optional[str] = None
    cuet_subject_8: Optional[str] = None
    cuet_total_score_8: Optional[str] = None
    cuet_score_obtained_8: Optional[str] = None
    cuet_subject_9: Optional[str] = None
    cuet_total_score_9: Optional[str] = None
    cuet_score_obtained_9: Optional[str] = None
    cuet_subject_10: Optional[str] = None
    cuet_total_score_10: Optional[str] = None
    cuet_score_obtained_10: Optional[str] = None
    
    cuet_total_score: Optional[str] = None
    
    # Document Checklist
    doc_admission_form: Optional[str] = None
    doc_undertaking_ragging: Optional[str] = None
    doc_photographs: Optional[str] = None
    doc_cuet_scorecard: Optional[str] = None
    doc_class_xii_marksheet: Optional[str] = None
    doc_class_x_certificate: Optional[str] = None
    doc_class_xii_certificate: Optional[str] = None
    doc_character_certificate: Optional[str] = None
    doc_transfer_certificate: Optional[str] = None
    doc_hindi_certificate: Optional[str] = None
    doc_caste_certificate: Optional[str] = None
    doc_sports_eca: Optional[str] = None
    doc_originals: Optional[str] = None
    doc_photo_id: Optional[str] = None
    
    additional_info: Optional[Dict[str, Any]] = None

class FormDetailResponse(FormResponse):
    extracted_data: Optional[ExtractedData] = None
    student_profile_id: Optional[int] = None
    documents: Optional[List["DocumentResponse"]] = None  # Populated at runtime
    
    # Name fields
    student_name: Optional[str] = None
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    surname: Optional[str] = None
    
    # Basic Personal Details
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    category: Optional[str] = None
    nationality: Optional[str] = None
    religion: Optional[str] = None
    aadhar_number: Optional[str] = None
    blood_group: Optional[str] = None
    below_poverty_line: Optional[str] = None
    minority_category: Optional[str] = None
    
    # Academic & Admission Details
    academic_session: Optional[str] = None
    course: Optional[str] = None
    admission_category: Optional[str] = None
    admission_category_other: Optional[str] = None
    du_portal_form_number: Optional[str] = None
    cuet_score: Optional[str] = None
    college_roll_no: Optional[str] = None
    date_of_admission: Optional[str] = None
    du_enrollment_number: Optional[str] = None
    hindi_medium_preference: Optional[str] = None
    
    # Address Details
    permanent_address: Optional[str] = None
    permanent_address_line1: Optional[str] = None
    permanent_address_line2: Optional[str] = None
    permanent_address_line3: Optional[str] = None
    permanent_state: Optional[str] = None
    permanent_pincode: Optional[str] = None
    correspondence_address: Optional[str] = None
    correspondence_address_line1: Optional[str] = None
    correspondence_address_line2: Optional[str] = None
    correspondence_address_line3: Optional[str] = None
    correspondence_state: Optional[str] = None
    correspondence_pincode: Optional[str] = None
    pincode: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    
    # Contact Details
    phone_number: Optional[str] = None
    alternate_phone: Optional[str] = None
    email: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    
    # Mother's Details
    mother_name: Optional[str] = None
    mother_occupation: Optional[str] = None
    mother_designation: Optional[str] = None
    mother_organization: Optional[str] = None
    mother_email: Optional[str] = None
    mother_mobile: Optional[str] = None
    mother_landline_code: Optional[str] = None
    mother_landline: Optional[str] = None
    mother_phone: Optional[str] = None
    
    # Father's Details
    father_name: Optional[str] = None
    father_occupation: Optional[str] = None
    father_designation: Optional[str] = None
    father_organization: Optional[str] = None
    father_email: Optional[str] = None
    father_mobile: Optional[str] = None
    father_landline_code: Optional[str] = None
    father_landline: Optional[str] = None
    father_phone: Optional[str] = None
    
    # Guardian Details
    guardian_name: Optional[str] = None
    guardian_relation: Optional[str] = None
    guardian_residential_address: Optional[str] = None
    guardian_organization: Optional[str] = None
    guardian_email: Optional[str] = None
    guardian_mobile: Optional[str] = None
    guardian_landline_code: Optional[str] = None
    guardian_landline: Optional[str] = None
    guardian_phone: Optional[str] = None
    
    # Family Income
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
    twelfth_roll_number: Optional[str] = None
    twelfth_institution: Optional[str] = None
    hindi_studied_upto: Optional[str] = None
    previous_qualification: Optional[str] = None
    graduation_details: Optional[str] = None
    
    # Course Application Details
    course_applied: Optional[str] = None
    application_number: Optional[str] = None
    enrollment_number: Optional[str] = None
    admission_date: Optional[str] = None
    
    # Certificate Details
    category_certificate_authority: Optional[str] = None
    category_certificate_number: Optional[str] = None
    category_certificate_date: Optional[str] = None
    disability_percentage: Optional[str] = None
    disability_type: Optional[str] = None
    udid_number: Optional[str] = None
    
    # CUET Marks
    cuet_subject_1: Optional[str] = None
    cuet_total_score_1: Optional[str] = None
    cuet_score_obtained_1: Optional[str] = None
    cuet_subject_2: Optional[str] = None
    cuet_total_score_2: Optional[str] = None
    cuet_score_obtained_2: Optional[str] = None
    cuet_subject_3: Optional[str] = None
    cuet_total_score_3: Optional[str] = None
    cuet_score_obtained_3: Optional[str] = None
    cuet_subject_4: Optional[str] = None
    cuet_total_score_4: Optional[str] = None
    cuet_score_obtained_4: Optional[str] = None
    cuet_subject_5: Optional[str] = None
    cuet_total_score_5: Optional[str] = None
    cuet_score_obtained_5: Optional[str] = None
    cuet_subject_6: Optional[str] = None
    cuet_total_score_6: Optional[str] = None
    cuet_score_obtained_6: Optional[str] = None
    
    # Extra CUET Marks (7-10)
    cuet_subject_7: Optional[str] = None
    cuet_total_score_7: Optional[str] = None
    cuet_score_obtained_7: Optional[str] = None
    cuet_subject_8: Optional[str] = None
    cuet_total_score_8: Optional[str] = None
    cuet_score_obtained_8: Optional[str] = None
    cuet_subject_9: Optional[str] = None
    cuet_total_score_9: Optional[str] = None
    cuet_score_obtained_9: Optional[str] = None
    cuet_subject_10: Optional[str] = None
    cuet_total_score_10: Optional[str] = None
    cuet_score_obtained_10: Optional[str] = None
    
    cuet_total_score: Optional[str] = None
    
    # Document Checklist
    doc_admission_form: Optional[str] = None
    doc_undertaking_ragging: Optional[str] = None
    doc_photographs: Optional[str] = None
    doc_cuet_scorecard: Optional[str] = None
    doc_class_xii_marksheet: Optional[str] = None
    doc_class_x_certificate: Optional[str] = None
    doc_class_xii_certificate: Optional[str] = None
    doc_character_certificate: Optional[str] = None
    doc_transfer_certificate: Optional[str] = None
    doc_hindi_certificate: Optional[str] = None
    doc_caste_certificate: Optional[str] = None
    doc_sports_eca: Optional[str] = None
    doc_originals: Optional[str] = None
    doc_photo_id: Optional[str] = None
    
    additional_info: Optional[Dict[str, Any]] = None
    verified_date: Optional[datetime] = None
    
    @model_validator(mode='before')
    @classmethod
    def extract_extra_cuet_fields(cls, data: Any) -> Any:
        # If input is an ORM object, it has additional_info attribute
        # If input is dict, it has additional_info key
        additional_info = None
        if hasattr(data, 'additional_info'):
            additional_info = data.additional_info
        elif isinstance(data, dict):
            additional_info = data.get('additional_info')
            
        if additional_info:
            # Create a dict of extra fields to patch into the object/dict
            extra_data = {}
            for i in range(7, 11):
                for suffix in ['subject', 'total_score', 'score_obtained']:
                    key = f'cuet_{suffix}_{i}'
                    if key in additional_info:
                        extra_data[key] = additional_info[key]
            
            # Apply extra data
            if isinstance(data, dict):
                data.update(extra_data)
            else:
                # For ORM objects, we can't set arbitrary attributes easily if it's strict,
                # but Pydantic 'from_attributes' reads attributes.
                # Since we can't modify the ORM object in-place safely without side effects, 
                # we convert it to a dict-like structure or just set attributes if allowed.
                # However, cleaner way for Pydantic v2 from_attributes is usually:
                # The validator runs *before* parsing.
                # If 'data' is the ORM object, we can just setattr on it assuming it's not immutable,
                # or better, return a wrapper/proxy.
                # Simplest: Just use setattr as it's a transient SQLAlchemy instance usually.
                for k, v in extra_data.items():
                    try:
                        setattr(data, k, v)
                    except:
                        pass
        return data

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

