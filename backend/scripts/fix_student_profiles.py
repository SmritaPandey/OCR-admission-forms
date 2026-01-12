"""
Script to fix incorrect student profiles and unlink forms from wrong profiles.
This will:
1. Delete student profiles with garbage/invalid names
2. Unlink forms from incorrect profiles
3. Keep only valid student profiles
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from sqlalchemy.orm import sessionmaker
from backend.database import engine, StudentProfile, AdmissionForm
import re

def is_valid_student_name(name: str) -> bool:
    """Check if a student name is valid (not garbage text)"""
    if not name or not name.strip():
        return False
    
    name = name.strip()
    
    # Check for common form label patterns that were incorrectly extracted
    invalid_patterns = [
        r'^of candidate',
        r'^IN BLOCK LETTERS',
        r'^of candidate only',
        r'^prescribed by the Govt',
        r'^Non- Creamy Layer',
        r'^Delhi University',
        r'^Government of India',
        r'^format prescribed',
        r'^candidates belonging',
        r'^central list',
        r'^valid certificate',
        r'^recent past',
        r'^mention of',
        r'^Delhi University rules',
        r'^who has taken',
        r'^father.*mother.*guardian',
        r'^undertake to ensure',
        r'^rules and regulations',
        r'^mandatory requirements',
        r'^form time to time',
        r'^declaration',
        r'^particulars filled',
        r'^true and correct',
        r'^best of my knowledge',
        r'^documents attached',
        r'^genuine in all respects',
        r'^fulfill the conditions',
        r'^eligibility criteria',
        r'^University of Delhi',
        r'^CUET Score',
        r'^abide by the rules',
        r'^College and University',
        r'^force from time',
        r'^applicable to students',
        r'^follow all rules',
        r'^regulations and procedures',
        r'^academic requirement',
        r'^minimum Attendance',
        r'^unable to fulfill',
        r'^appropriate action',
        r'^disciplinary jurisdiction',
        r'^Principal.*Vice-Chancellor',
        r'^autorities of the University',
        r'^vested with the power',
        r'^exercise discipline',
        r'^Act.*Statutes.*Ordinances',
        r'^rules framed',
        r'^not pursuing',
        r'^professional course',
        r'^CA.*CWA.*CS.*LLB',
        r'^simultaneously while',
        r'^undergraduate studies',
        r'^failing which',
        r'^admission.*cancelled',
        r'^document submitted',
        r'^found to be false',
        r'^action may be taken',
        r'^College.*University of Delhi',
    ]
    
    name_lower = name.lower()
    for pattern in invalid_patterns:
        if re.search(pattern, name_lower, re.IGNORECASE):
            return False
    
    # Check if name is too long (likely garbage)
    if len(name) > 200:
        return False
    
    # Check if name has too many words (likely garbage)
    if len(name.split()) > 20:
        return False
    
    # Check if it's mostly special characters or numbers
    if len(re.sub(r'[a-zA-Z\s]', '', name)) > len(name) * 0.5:
        return False
    
    return True

def fix_student_profiles():
    """Fix student profiles by removing invalid ones and unlinking forms"""
    Session = sessionmaker(bind=engine)
    db = Session()
    
    try:
        # Get all student profiles
        all_profiles = db.query(StudentProfile).all()
        
        print(f"Found {len(all_profiles)} student profiles")
        
        invalid_profiles = []
        valid_profiles = []
        
        for profile in all_profiles:
            if is_valid_student_name(profile.student_name):
                valid_profiles.append(profile)
            else:
                invalid_profiles.append(profile)
        
        print(f"\nValid profiles: {len(valid_profiles)}")
        print(f"Invalid profiles: {len(invalid_profiles)}")
        
        if invalid_profiles:
            print("\n=== Invalid Profiles to Delete ===")
            for profile in invalid_profiles:
                # Count forms linked to this profile
                form_count = db.query(AdmissionForm).filter(
                    AdmissionForm.student_profile_id == profile.id
                ).count()
                
                print(f"  ID: {profile.id}, Name: '{profile.student_name[:50]}...', Forms: {form_count}")
                
                # Unlink all forms from this invalid profile
                db.query(AdmissionForm).filter(
                    AdmissionForm.student_profile_id == profile.id
                ).update({AdmissionForm.student_profile_id: None})
                
                # Delete the invalid profile
                db.delete(profile)
        
        db.commit()
        
        print(f"\n✅ Cleaned up {len(invalid_profiles)} invalid profiles")
        print(f"✅ Unlinked forms from invalid profiles")
        
        # Show remaining valid profiles
        remaining = db.query(StudentProfile).all()
        print(f"\n=== Remaining Valid Profiles ({len(remaining)}) ===")
        for profile in remaining:
            form_count = db.query(AdmissionForm).filter(
                AdmissionForm.student_profile_id == profile.id
            ).count()
            print(f"  ID: {profile.id}, Name: {profile.student_name}, Aadhar: {profile.aadhar_number}, Forms: {form_count}")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    print("🔧 Fixing student profiles...")
    fix_student_profiles()
    print("\n✅ Done!")

