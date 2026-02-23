"""
Test script for student search functionality.
Tests the backend API endpoints and database integration.
"""
import sys
import os
import requests
import json
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.database import SessionLocal, StudentProfile
from backend.api.routes.students import get_or_create_student_profile

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

def test_database_operations():
    """Test database operations for student profiles."""
    print("\n=== Testing Database Operations ===")
    db = SessionLocal()
    try:
        # Test creating a student profile with roll number
        print("\n1. Creating student profile with roll number...")
        profile = get_or_create_student_profile(
            db=db,
            student_name="Test Student",
            aadhar_number="123456789012",
            roll_number="ROLL001"
        )
        print(f"   ✓ Created profile: ID={profile.id}, Name={profile.student_name}, Roll={profile.roll_number}")
        
        # Test searching by roll number
        print("\n2. Searching by roll number...")
        from sqlalchemy import or_
        results = db.query(StudentProfile).filter(
            StudentProfile.roll_number.ilike("%ROLL001%")
        ).all()
        print(f"   ✓ Found {len(results)} student(s) with roll number containing 'ROLL001'")
        
        # Test listing all students
        print("\n3. Listing all students...")
        all_students = db.query(StudentProfile).order_by(StudentProfile.updated_date.desc()).limit(10).all()
        print(f"   ✓ Found {len(all_students)} student(s) in database")
        
        return True
    except Exception as e:
        print(f"   ✗ Database test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

def test_api_endpoints():
    """Test API endpoints for student search."""
    print("\n=== Testing API Endpoints ===")
    
    try:
        # Test listing all students
        print("\n1. Testing GET /api/students/ (list all)...")
        response = requests.get(f"{API_BASE_URL}/api/students/", params={"limit": 10})
        if response.status_code == 200:
            students = response.json()
            print(f"   ✓ Successfully retrieved {len(students)} students")
            if students:
                print(f"   ✓ Sample student: {students[0].get('student_name', 'N/A')}")
        else:
            print(f"   ✗ Failed with status {response.status_code}: {response.text}")
            return False
        
        # Test searching by name
        print("\n2. Testing search by student name...")
        response = requests.get(
            f"{API_BASE_URL}/api/students/",
            params={"student_name": "Test", "limit": 10}
        )
        if response.status_code == 200:
            students = response.json()
            print(f"   ✓ Found {len(students)} student(s) matching 'Test'")
        else:
            print(f"   ✗ Failed with status {response.status_code}: {response.text}")
            return False
        
        # Test searching by roll number
        print("\n3. Testing search by roll number...")
        response = requests.get(
            f"{API_BASE_URL}/api/students/",
            params={"roll_number": "ROLL", "limit": 10}
        )
        if response.status_code == 200:
            students = response.json()
            print(f"   ✓ Found {len(students)} student(s) with roll number containing 'ROLL'")
        else:
            print(f"   ✗ Failed with status {response.status_code}: {response.text}")
            return False
        
        # Test search results endpoint
        print("\n4. Testing GET /api/students/search/results...")
        response = requests.get(
            f"{API_BASE_URL}/api/students/search/results",
            params={"student_name": "Test", "roll_number": "ROLL", "limit": 10}
        )
        if response.status_code == 200:
            students = response.json()
            print(f"   ✓ Search results endpoint returned {len(students)} student(s)")
        else:
            print(f"   ✗ Failed with status {response.status_code}: {response.text}")
            return False
        
        return True
        
    except requests.exceptions.ConnectionError:
        print("   ⚠ Could not connect to API. Is the server running?")
        print("   Run: python -m uvicorn backend.main:app --reload")
        return False
    except Exception as e:
        print(f"   ✗ API test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("Student Search Functionality Test")
    print("=" * 60)
    
    # Test database operations
    db_success = test_database_operations()
    
    # Test API endpoints
    api_success = test_api_endpoints()
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Database Operations: {'✓ PASSED' if db_success else '✗ FAILED'}")
    print(f"API Endpoints: {'✓ PASSED' if api_success else '✗ FAILED'}")
    
    if db_success and api_success:
        print("\n✓ All tests passed!")
        return 0
    else:
        print("\n✗ Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())


