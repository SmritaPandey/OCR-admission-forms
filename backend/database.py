from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Enum as SQLEnum, JSON, ForeignKey, BigInteger, Index
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

class DocumentCategory(str, enum.Enum):
    ID_PROOF = "ID Proof"
    ACADEMIC_CERTIFICATE = "Academic Certificate"
    MEDICAL_CERTIFICATE = "Medical Certificate"
    BIRTH_CERTIFICATE = "Birth Certificate"
    INCOME_CERTIFICATE = "Income Certificate"
    CASTE_CERTIFICATE = "Caste Certificate"
    OTHER = "Other"

class StudentProfile(Base):
    __tablename__ = "student_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    student_name = Column(String, nullable=False, index=True)
    aadhar_number = Column(String, nullable=True, index=True)
    created_date = Column(DateTime, default=datetime.utcnow)
    updated_date = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    forms = relationship("AdmissionForm", back_populates="student_profile")
    documents = relationship("StudentDocument", back_populates="student_profile")
    
    __table_args__ = (
        Index('idx_student_name_aadhar', 'student_name', 'aadhar_number'),
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
    student_profile = relationship("StudentProfile", back_populates="forms")
    documents = relationship("StudentDocument", back_populates="form")
    
    # Verified student information - Basic Details
    student_name = Column(String, nullable=True)
    date_of_birth = Column(String, nullable=True)
    gender = Column(String, nullable=True)
    category = Column(String, nullable=True)  # General/OBC/SC/ST/etc.
    nationality = Column(String, nullable=True)
    religion = Column(String, nullable=True)
    aadhar_number = Column(String, nullable=True)
    blood_group = Column(String, nullable=True)
    
    # Address Details
    permanent_address = Column(Text, nullable=True)
    correspondence_address = Column(Text, nullable=True)
    pincode = Column(String, nullable=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    
    # Contact Details
    phone_number = Column(String, nullable=True)
    alternate_phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    emergency_contact_name = Column(String, nullable=True)
    emergency_contact_phone = Column(String, nullable=True)
    
    # Guardian/Parent Details
    father_name = Column(String, nullable=True)
    father_occupation = Column(String, nullable=True)
    father_phone = Column(String, nullable=True)
    mother_name = Column(String, nullable=True)
    mother_occupation = Column(String, nullable=True)
    mother_phone = Column(String, nullable=True)
    guardian_name = Column(String, nullable=True)
    guardian_relation = Column(String, nullable=True)
    guardian_phone = Column(String, nullable=True)
    annual_income = Column(String, nullable=True)
    
    # Educational Qualifications
    tenth_board = Column(String, nullable=True)
    tenth_year = Column(String, nullable=True)
    tenth_percentage = Column(String, nullable=True)
    tenth_school = Column(String, nullable=True)
    twelfth_board = Column(String, nullable=True)
    twelfth_year = Column(String, nullable=True)
    twelfth_percentage = Column(String, nullable=True)
    twelfth_school = Column(String, nullable=True)
    previous_qualification = Column(String, nullable=True)
    graduation_details = Column(Text, nullable=True)
    
    # Course Application Details
    course_applied = Column(String, nullable=True)
    application_number = Column(String, nullable=True)
    admission_date = Column(String, nullable=True)
    
    # Additional Information
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

