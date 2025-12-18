"""
Document Manager Utility
Organize and manage documents for student records
"""
from pathlib import Path
from typing import List, Dict, Optional
from backend.config import settings
import os

class DocumentManager:
    """Manage document storage and organization"""
    
    def __init__(self):
        self.upload_dir = Path(settings.UPLOAD_DIR).resolve()
        self.documents_dir = self.upload_dir / "documents"
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure required directories exist"""
        self.documents_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories for organization
        (self.documents_dir / "by_student").mkdir(exist_ok=True)
        (self.documents_dir / "by_category").mkdir(exist_ok=True)
    
    def get_student_document_path(self, student_id: int, filename: str) -> Path:
        """Get path for a student document"""
        student_dir = self.documents_dir / "by_student" / str(student_id)
        student_dir.mkdir(parents=True, exist_ok=True)
        return student_dir / filename
    
    def get_category_document_path(self, category: str, filename: str) -> Path:
        """Get path for a document organized by category"""
        category_dir = self.documents_dir / "by_category" / category.replace(" ", "_")
        category_dir.mkdir(parents=True, exist_ok=True)
        return category_dir / filename
    
    def get_document_file_path(self, relative_path: str) -> Path:
        """Get full file path from relative path"""
        return self.upload_dir / relative_path
    
    def list_student_documents(self, student_id: int) -> List[Dict[str, str]]:
        """List all documents for a student"""
        student_dir = self.documents_dir / "by_student" / str(student_id)
        if not student_dir.exists():
            return []
        
        documents = []
        for file_path in student_dir.iterdir():
            if file_path.is_file():
                documents.append({
                    "filename": file_path.name,
                    "path": str(file_path.relative_to(self.upload_dir)),
                    "size": file_path.stat().st_size
                })
        
        return documents
    
    def get_document_size(self, relative_path: str) -> Optional[int]:
        """Get file size in bytes"""
        file_path = self.get_document_file_path(relative_path)
        if file_path.exists():
            return file_path.stat().st_size
        return None
    
    def document_exists(self, relative_path: str) -> bool:
        """Check if document file exists"""
        file_path = self.get_document_file_path(relative_path)
        return file_path.exists()
    
    def delete_document_file(self, relative_path: str) -> bool:
        """Delete document file from disk"""
        file_path = self.get_document_file_path(relative_path)
        if file_path.exists():
            try:
                file_path.unlink()
                return True
            except Exception as e:
                print(f"Error deleting file {file_path}: {e}")
                return False
        return False

# Global instance
document_manager = DocumentManager()

