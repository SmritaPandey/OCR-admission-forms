from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from backend.database import DocumentCategory

class DocumentCreate(BaseModel):
    document_category: DocumentCategory
    description: Optional[str] = None
    form_id: Optional[int] = None
    student_profile_id: Optional[int] = None

class DocumentResponse(BaseModel):
    id: int
    filename: str
    file_path: str
    upload_date: datetime
    document_category: DocumentCategory
    description: Optional[str] = None
    file_size: int
    form_id: Optional[int] = None
    student_profile_id: Optional[int] = None
    
    class Config:
        from_attributes = True

class DocumentDetailResponse(DocumentResponse):
    """Extended response with full details"""
    pass

