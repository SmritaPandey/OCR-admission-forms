#!/usr/bin/env python3
"""
Clear all forms and student data from the database
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.database import SessionLocal, AdmissionForm, StudentProfile, StudentDocument
from backend.config import settings
import os
from pathlib import Path as PathLib

def clear_all_data():
    """Delete all forms, student profiles, and documents"""
    db = SessionLocal()
    
    try:
        print("🗑️  Clearing all data from database...")
        
        # Delete all documents first (foreign key constraints)
        documents_count = db.query(StudentDocument).count()
        if documents_count > 0:
            db.query(StudentDocument).delete()
            print(f"   Deleted {documents_count} documents")
        
        # Delete all forms
        forms = db.query(AdmissionForm).all()
        forms_count = len(forms)
        
        if forms_count > 0:
            # Delete associated files
            upload_dir = PathLib(settings.UPLOAD_DIR).resolve()
            for form in forms:
                if form.file_path:
                    full_path = upload_dir / form.file_path
                    if full_path.exists():
                        try:
                            os.remove(full_path)
                            print(f"   Deleted file: {form.filename}")
                        except Exception as e:
                            print(f"   Warning: Could not delete {form.filename}: {e}")
            
            db.query(AdmissionForm).delete()
            print(f"   Deleted {forms_count} forms")
        
        # Delete all student profiles
        profiles_count = db.query(StudentProfile).count()
        if profiles_count > 0:
            db.query(StudentProfile).delete()
            print(f"   Deleted {profiles_count} student profiles")
        
        db.commit()
        print("✅ All data cleared successfully!")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error clearing data: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    clear_all_data()

