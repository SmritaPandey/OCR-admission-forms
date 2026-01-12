"""
Script to link forms with student names to student profiles.
This will create profiles for forms that have student_name but aren't linked.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from sqlalchemy.orm import sessionmaker
from backend.database import engine, StudentProfile, AdmissionForm
from backend.api.routes.students import get_or_create_student_profile

def is_valid_student_name(name: str) -> bool:
    """Check if a student name is valid"""
    if not name or not name.strip():
        return False
    
    name = name.strip()
    
    # Check for common invalid patterns
    invalid_patterns = [
        'of candidate',
        'IN BLOCK LETTERS',
        'prescribed by',
        'Government of India',
        'Delhi University',
        'who has taken',
        'father.*mother',
        'undertake',
        'declaration',
        'particulars',
    ]
    
    import re
    name_lower = name.lower()
    for pattern in invalid_patterns:
        if re.search(pattern, name_lower, re.IGNORECASE):
            return False
    
    # Check if name is too long or has too many words
    if len(name) > 100 or len(name.split()) > 10:
        return False
    
    return True

def link_forms_to_profiles():
    """Link forms with student names to student profiles"""
    Session = sessionmaker(bind=engine)
    db = Session()
    
    try:
        # Get all forms that have a student_name but no profile linked
        forms = db.query(AdmissionForm).filter(
            AdmissionForm.student_name.isnot(None),
            AdmissionForm.student_profile_id.is_(None)
        ).all()
        
        print(f"Found {len(forms)} forms with student names but no profile")
        
        linked_count = 0
        skipped_count = 0
        
        for form in forms:
            student_name = form.student_name.strip() if form.student_name else None
            
            if not student_name or not is_valid_student_name(student_name):
                print(f"  ⏭️  Skipping Form {form.id} ({form.filename}): Invalid name '{student_name}'")
                skipped_count += 1
                continue
            
            try:
                # Get or create student profile
                profile = get_or_create_student_profile(
                    db,
                    student_name,
                    form.aadhar_number
                )
                
                # Link form to profile
                form.student_profile_id = profile.id
                db.commit()
                
                print(f"  ✅ Linked Form {form.id} ({form.filename}) → Profile {profile.id} ({profile.student_name})")
                linked_count += 1
                
            except Exception as e:
                db.rollback()
                print(f"  ❌ Error linking Form {form.id}: {e}")
        
        print(f"\n✅ Linked {linked_count} forms to profiles")
        print(f"⏭️  Skipped {skipped_count} forms with invalid names")
        
        # Show summary
        total_profiles = db.query(StudentProfile).count()
        total_forms_linked = db.query(AdmissionForm).filter(
            AdmissionForm.student_profile_id.isnot(None)
        ).count()
        
        print(f"\n📊 Summary:")
        print(f"   Total Profiles: {total_profiles}")
        print(f"   Total Forms Linked: {total_forms_linked}")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    print("🔗 Linking forms to student profiles...")
    link_forms_to_profiles()
    print("\n✅ Done!")

