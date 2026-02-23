from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Enum as SQLEnum, JSON, ForeignKey, BigInteger, Index, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import enum
from backend.config import settings

# Support SQLite with check_same_thread=False
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class FormStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    EXTRACTING = "extracting"
    EXTRACTED = "extracted"
    VERIFIED = "verified"
    ERROR = "error"

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    STAFF = "staff"
    VIEWER = "viewer"


class DocumentCategory(str, enum.Enum):
    ID_PROOF = "ID Proof"
    ACADEMIC_CERTIFICATE = "Academic Certificate"
    MEDICAL_CERTIFICATE = "Medical Certificate"
    BIRTH_CERTIFICATE = "Birth Certificate"
    INCOME_CERTIFICATE = "Income Certificate"
    CASTE_CERTIFICATE = "Caste Certificate"
    OTHER = "Other"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(128), nullable=False, unique=True, index=True)
    email = Column(String(256), nullable=True, index=True)
    hashed_password = Column(String(256), nullable=False)
    role = Column(String(32), nullable=False, default=UserRole.VIEWER.value, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (Index("idx_users_username", "username"),)


class StudentProfile(Base):
    __tablename__ = "student_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    student_name = Column(String, nullable=False, index=True)
    aadhar_number = Column(String, nullable=True, index=True)
    roll_number = Column(String, nullable=True, index=True)  # Student roll number for search
    is_verified = Column(Boolean, default=False, index=True)  # Verified status
    created_date = Column(DateTime, default=datetime.utcnow)
    updated_date = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    forms = relationship("AdmissionForm", back_populates="student_profile", cascade="all, delete-orphan")
    documents = relationship("StudentDocument", back_populates="student_profile", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_student_name_aadhar', 'student_name', 'aadhar_number'),
        Index('idx_student_roll', 'roll_number'),
    )
    
class AdmissionForm(Base):
    __tablename__ = "admission_forms"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    upload_date = Column(DateTime, default=datetime.utcnow)
    ocr_provider = Column(String, nullable=False)
    status = Column(SQLEnum(FormStatus), default=FormStatus.UPLOADED)
    
    # Link to student profile
    student_profile_id = Column(Integer, ForeignKey("student_profiles.id"), nullable=True, index=True)
    
    # OCR extracted data (raw JSON)
    extracted_data = Column(JSON, nullable=True)
    
    # Relationships
    student_profile = relationship("StudentProfile", back_populates="forms", lazy="select")
    documents = relationship("StudentDocument", back_populates="form", lazy="select", cascade="all, delete-orphan")  # Use cascade for automatic cleanup
    
    # ============================================
    # PAGE 1: ACADEMIC & ADMISSION DETAILS (in form order)
    # ============================================
    academic_session = Column(String, nullable=True)  # Academic Session
    course = Column(String, nullable=True)  # Course selection: B.COM.(H) / B.A.(H) ECO
    admission_category = Column(String, nullable=True)  # GEN/OBC/SC/ST/Sports/PwD/EWS/Foreign/CW/KM/Others/ECA
    admission_category_other = Column(String, nullable=True)  # Other (Specify) if "Others" selected
    du_portal_form_number = Column(String, nullable=True)  # DU Portal Form Number
    cuet_score = Column(String, nullable=True)  # CUET Score
    college_roll_no = Column(String, nullable=True, index=True)  # College Roll No.
    date_of_admission = Column(String, nullable=True)  # Date of Admission
    
    # ============================================
    # PAGE 1: PERSONAL DETAILS (in form order)
    # ============================================
    # Name fields (separate components)
    first_name = Column(String, nullable=True)
    middle_name = Column(String, nullable=True)
    surname = Column(String, nullable=True)
    student_name = Column(String, nullable=True)  # Full name (combined)
    
    # Personal information
    gender = Column(String, nullable=True)  # Male/Female/Transgender
    date_of_birth = Column(String, nullable=True)
    category = Column(String, nullable=True)  # Reservation category (may differ from admission_category)
    nationality = Column(String, nullable=True)
    religion = Column(String, nullable=True)
    aadhar_number = Column(String, nullable=True)
    blood_group = Column(String, nullable=True)
    below_poverty_line = Column(String, nullable=True)  # Whether Below Poverty Line (Yes/No)
    minority_category = Column(String, nullable=True)  # Muslim/Jain/Sikh/Persian/Christian/Buddhists/Others
    
    # ============================================
    # PAGE 1: ADDRESS DETAILS (in form order)
    # ============================================
    # Permanent Address
    permanent_address_line1 = Column(Text, nullable=True)
    permanent_address_line2 = Column(Text, nullable=True)
    permanent_address_line3 = Column(Text, nullable=True)
    permanent_state = Column(String, nullable=True)
    permanent_pincode = Column(String, nullable=True)
    permanent_address = Column(Text, nullable=True)  # Combined address (for backward compatibility)
    
    # Correspondence Address
    correspondence_address_line1 = Column(Text, nullable=True)
    correspondence_address_line2 = Column(Text, nullable=True)
    correspondence_address_line3 = Column(Text, nullable=True)
    correspondence_state = Column(String, nullable=True)
    correspondence_pincode = Column(String, nullable=True)
    correspondence_address = Column(Text, nullable=True)  # Combined address (for backward compatibility)
    
    # Legacy fields (kept for backward compatibility)
    pincode = Column(String, nullable=True)  # Use permanent_pincode or correspondence_pincode
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)  # Use permanent_state or correspondence_state
    
    # Contact Details
    phone_number = Column(String, nullable=True)
    alternate_phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    emergency_contact_name = Column(String, nullable=True)
    emergency_contact_phone = Column(String, nullable=True)
    
    # ============================================
    # PAGE 1: PARENT NAMES (in form order)
    # ============================================
    mother_name = Column(String, nullable=True)
    father_name = Column(String, nullable=True)
    
    # ============================================
    # PAGE 1: CUET MARKS TABLE (in form order)
    # ============================================
    cuet_subject_1 = Column(String, nullable=True)
    cuet_total_score_1 = Column(String, nullable=True)
    cuet_score_obtained_1 = Column(String, nullable=True)
    cuet_subject_2 = Column(String, nullable=True)
    cuet_total_score_2 = Column(String, nullable=True)
    cuet_score_obtained_2 = Column(String, nullable=True)
    cuet_subject_3 = Column(String, nullable=True)
    cuet_total_score_3 = Column(String, nullable=True)
    cuet_score_obtained_3 = Column(String, nullable=True)
    cuet_subject_4 = Column(String, nullable=True)
    cuet_total_score_4 = Column(String, nullable=True)
    cuet_score_obtained_4 = Column(String, nullable=True)
    cuet_subject_5 = Column(String, nullable=True)
    cuet_total_score_5 = Column(String, nullable=True)
    cuet_score_obtained_5 = Column(String, nullable=True)
    cuet_subject_6 = Column(String, nullable=True)
    cuet_total_score_6 = Column(String, nullable=True)
    cuet_score_obtained_6 = Column(String, nullable=True)
    cuet_total_score = Column(String, nullable=True)  # Total CUET Score

    # ============================================
    # PAGE 4: DOCUMENT CHECKLIST
    # ============================================
    doc_admission_form = Column(String, nullable=True)  # Yes/No
    doc_undertaking_ragging = Column(String, nullable=True)
    doc_photographs = Column(String, nullable=True)
    doc_cuet_scorecard = Column(String, nullable=True)
    doc_class_xii_marksheet = Column(String, nullable=True)
    doc_class_x_certificate = Column(String, nullable=True)
    doc_class_xii_certificate = Column(String, nullable=True)
    doc_character_certificate = Column(String, nullable=True)
    doc_transfer_certificate = Column(String, nullable=True)
    doc_hindi_certificate = Column(String, nullable=True)
    doc_caste_certificate = Column(String, nullable=True)
    doc_sports_eca = Column(String, nullable=True)
    doc_originals = Column(String, nullable=True)
    doc_photo_id = Column(String, nullable=True)

    # ============================================
    # PAGE 2: SECTION 11 - QUALIFYING EXAMINATION (in form order)
    # ============================================
    twelfth_year = Column(String, nullable=True)
    twelfth_board = Column(String, nullable=True)
    twelfth_roll_number = Column(String, nullable=True)  # Examination Roll No.
    twelfth_institution = Column(String, nullable=True)  # Institution Last Attended
    hindi_studied_upto = Column(String, nullable=True)  # VIII/X/XII/Never
    
    # ============================================
    # PAGE 2: SECTION 12 - PERSONAL INFORMATION (in form order)
    # ============================================
    # (nationality, religion, blood_group, below_poverty_line, minority_category already defined above)
    annual_income = Column(String, nullable=True)  # Parent's / Family Annual Income
    
    # ============================================
    # PAGE 2: SECTION 13 - MOTHER'S OCCUPATIONAL DETAILS (in form order)
    # ============================================
    # (mother_name already defined above)
    mother_occupation = Column(String, nullable=True)
    mother_designation = Column(String, nullable=True)  # Designation (if employed)
    mother_organization = Column(Text, nullable=True)  # Organization & Address
    mother_email = Column(String, nullable=True)
    mother_mobile = Column(String, nullable=True)  # Mobile No. (10 digits)
    mother_landline_code = Column(String, nullable=True)  # Landline Code (3 digits)
    mother_landline = Column(String, nullable=True)  # Landline No. (8 digits)
    mother_phone = Column(String, nullable=True)  # Combined phone (for backward compatibility)
    
    # ============================================
    # PAGE 2: SECTION 14 - FATHER'S OCCUPATIONAL DETAILS (in form order)
    # ============================================
    # (father_name already defined above)
    father_occupation = Column(String, nullable=True)
    father_designation = Column(String, nullable=True)  # Designation (if employed)
    father_organization = Column(Text, nullable=True)  # Organization & Address
    father_email = Column(String, nullable=True)
    father_mobile = Column(String, nullable=True)  # Mobile No. (10 digits)
    father_landline_code = Column(String, nullable=True)  # Landline Code (3 digits)
    father_landline = Column(String, nullable=True)  # Landline No. (8 digits)
    father_phone = Column(String, nullable=True)  # Combined phone (for backward compatibility)
    
    # ============================================
    # PAGE 2: SECTION 15 - LOCAL GUARDIAN'S DETAILS (in form order)
    # ============================================
    guardian_name = Column(String, nullable=True)
    guardian_residential_address = Column(Text, nullable=True)  # Residential Address
    guardian_organization = Column(Text, nullable=True)  # Organization & Address
    guardian_email = Column(String, nullable=True)
    guardian_mobile = Column(String, nullable=True)  # Mobile No. (10 digits)
    guardian_landline_code = Column(String, nullable=True)  # Landline Code (3 digits)
    guardian_landline = Column(String, nullable=True)  # Landline No. (8 digits)
    guardian_relation = Column(String, nullable=True)  # Relationship
    guardian_phone = Column(String, nullable=True)  # Combined phone (for backward compatibility)
    
    # ============================================
    # PAGE 2: SECTION 16 - OTHER INFORMATION (in form order)
    # ============================================
    du_enrollment_number = Column(String, nullable=True)  # Delhi University Enrolment No.
    hindi_medium_preference = Column(String, nullable=True)  # Yes/No
    
    # ============================================
    # PAGE 2: SECTION 17 - EWS/SC/ST/OBC/PwBD DETAILS (in form order)
    # ============================================
    category_certificate_authority = Column(Text, nullable=True)  # Name & Address of certificate issuing authority
    category_certificate_number = Column(String, nullable=True)  # Certificate No.
    category_certificate_date = Column(String, nullable=True)  # Date of Issue
    disability_percentage = Column(String, nullable=True)  # Extent of disability (%)
    disability_type = Column(String, nullable=True)  # VH/HH/OH
    udid_number = Column(String, nullable=True)  # UDID No.
    
    # ============================================
    # EDUCATIONAL QUALIFICATIONS (legacy - kept for backward compatibility)
    # ============================================
    tenth_board = Column(String, nullable=True)
    tenth_year = Column(String, nullable=True)
    tenth_percentage = Column(String, nullable=True)
    tenth_school = Column(String, nullable=True)
    # (twelfth_year, twelfth_board already defined above)
    twelfth_percentage = Column(String, nullable=True)
    twelfth_school = Column(String, nullable=True)
    previous_qualification = Column(String, nullable=True)
    graduation_details = Column(Text, nullable=True)
    
    # ============================================
    # COURSE APPLICATION DETAILS (legacy - kept for backward compatibility)
    # ============================================
    course_applied = Column(String, nullable=True)  # May differ from 'course' field
    application_number = Column(String, nullable=True)  # May differ from 'du_portal_form_number'
    enrollment_number = Column(String, nullable=True, index=True)  # May differ from 'du_enrollment_number'
    # (admission_date already defined above)
    
    # ============================================
    # PAGE 3: DOCUMENTS REQUIRED (in form order)
    # ============================================
    document_printed_admission_form = Column(String, nullable=True)  # Boolean as string
    document_anti_ragging_undertaking = Column(String, nullable=True)
    document_photographs_pasted = Column(String, nullable=True)
    document_cuet_score_card = Column(String, nullable=True)
    document_twelfth_mark_sheet = Column(String, nullable=True)
    document_tenth_certificate = Column(String, nullable=True)
    document_twelfth_certificate = Column(String, nullable=True)
    document_character_certificate = Column(String, nullable=True)
    document_transfer_certificate = Column(String, nullable=True)
    document_migration_certificate = Column(String, nullable=True)
    document_hindi_exemption_certificate = Column(String, nullable=True)
    document_caste_category_certificate = Column(String, nullable=True)
    document_sports_eca_certificates = Column(String, nullable=True)
    document_original_certificates = Column(String, nullable=True)
    document_photo_id_proofs = Column(String, nullable=True)
    
    # ============================================
    # PAGE 4: DECLARATIONS (in form order)
    # ============================================
    # Student Declaration
    student_declaration_name = Column(String, nullable=True)
    student_declaration_date = Column(String, nullable=True)
    student_declaration_place = Column(String, nullable=True)
    student_declaration_signature = Column(String, nullable=True)  # Path to signature image
    
    # Parent/Guardian Declaration
    parent_guardian_name = Column(String, nullable=True)
    parent_guardian_relationship = Column(String, nullable=True)  # Father/Mother/Guardian
    parent_guardian_candidate_name = Column(String, nullable=True)
    parent_guardian_course = Column(String, nullable=True)  # Bachelor's Program/Course
    parent_guardian_date = Column(String, nullable=True)
    parent_guardian_place = Column(String, nullable=True)
    parent_guardian_signature = Column(String, nullable=True)  # Path to signature image
    
    # ============================================
    # ADDITIONAL INFORMATION & METADATA
    # ============================================
    additional_info = Column(JSON, nullable=True)  # For flexible additional fields
    
    verified_date = Column(DateTime, nullable=True)
    verified_by = Column(String, nullable=True)

class StudentDocument(Base):
    __tablename__ = "student_documents"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    upload_date = Column(DateTime, default=datetime.utcnow)
    document_category = Column(SQLEnum(DocumentCategory), nullable=False, index=True)
    description = Column(Text, nullable=True)
    file_size = Column(BigInteger, nullable=False)  # Size in bytes
    
    # Link to either form or student profile (at least one must be set)
    form_id = Column(Integer, ForeignKey("admission_forms.id"), nullable=True, index=True)
    student_profile_id = Column(Integer, ForeignKey("student_profiles.id"), nullable=True, index=True)
    
    # Relationships
    form = relationship("AdmissionForm", back_populates="documents")
    student_profile = relationship("StudentProfile", back_populates="documents")
    
    __table_args__ = (
        Index('idx_form_category', 'form_id', 'document_category'),
        Index('idx_profile_category', 'student_profile_id', 'document_category'),
    )

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

