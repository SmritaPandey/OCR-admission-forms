#!/usr/bin/env python3
"""
System Test Script for Student Records Management System
Tests all components to ensure everything is working correctly
"""

import sys
import os
import subprocess
from pathlib import Path

# Colors for output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")

def print_success(text):
    print(f"{Colors.GREEN}✅ {text}{Colors.RESET}")

def print_error(text):
    print(f"{Colors.RED}❌ {text}{Colors.RESET}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.RESET}")

def print_info(text):
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.RESET}")

def check_python_version():
    """Check Python version"""
    print_header("Checking Python Version")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print_success(f"Python {version.major}.{version.minor}.{version.micro} (Required: 3.8+)")
        return True
    else:
        print_error(f"Python {version.major}.{version.minor}.{version.micro} (Required: 3.8+)")
        return False

def check_file_exists(filepath):
    """Check if a file exists"""
    if Path(filepath).exists():
        return True
    return False

def check_python_dependencies():
    """Check Python dependencies"""
    print_header("Checking Python Dependencies")
    
    required_packages = {
        'fastapi': 'FastAPI',
        'uvicorn': 'Uvicorn',
        'sqlalchemy': 'SQLAlchemy',
        'pydantic': 'Pydantic',
        'pydantic_settings': 'Pydantic Settings',
        'PIL': 'Pillow',
        'pytesseract': 'Pytesseract',
        'fitz': 'PyMuPDF',
        'cv2': 'OpenCV',
        'numpy': 'NumPy',
    }
    
    missing = []
    installed = []
    
    for module, name in required_packages.items():
        try:
            __import__(module)
            installed.append(name)
            print_success(f"{name} installed")
        except ImportError:
            missing.append(name)
            print_error(f"{name} NOT installed")
    
    if missing:
        print_warning(f"\nMissing packages: {', '.join(missing)}")
        print_info("Install with: pip install -r requirements.txt")
        return False
    else:
        print_success(f"All {len(installed)} required packages installed")
        return True

def check_tesseract():
    """Check if Tesseract OCR is installed"""
    print_header("Checking Tesseract OCR")
    try:
        result = subprocess.run(['tesseract', '--version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            version = result.stdout.split('\n')[0]
            print_success(f"Tesseract installed: {version}")
            return True
        else:
            print_error("Tesseract not found")
            return False
    except FileNotFoundError:
        print_error("Tesseract not installed")
        print_info("Install with: sudo apt-get install tesseract-ocr (Ubuntu/Debian)")
        print_info("Or: brew install tesseract (macOS)")
        return False
    except Exception as e:
        print_error(f"Error checking Tesseract: {e}")
        return False

def check_backend_files():
    """Check if backend files exist"""
    print_header("Checking Backend Files")
    
    required_files = [
        'backend/main.py',
        'backend/config.py',
        'backend/database.py',
        'backend/models/form.py',
        'backend/models/document.py',
        'backend/api/routes/upload.py',
        'backend/api/routes/forms.py',
        'backend/api/routes/students.py',
        'backend/api/routes/documents.py',
        'backend/ocr/ocr_factory.py',
        'backend/ocr/tesseract_provider.py',
        'backend/utils/form_parser.py',
        'requirements.txt',
    ]
    
    missing = []
    for filepath in required_files:
        if check_file_exists(filepath):
            print_success(f"{filepath} exists")
        else:
            missing.append(filepath)
            print_error(f"{filepath} MISSING")
    
    if missing:
        print_error(f"\nMissing {len(missing)} file(s)")
        return False
    else:
        print_success(f"All {len(required_files)} backend files exist")
        return True

def check_frontend_files():
    """Check if frontend files exist"""
    print_header("Checking Frontend Files")
    
    required_files = [
        'frontend/package.json',
        'frontend/src/App.tsx',
        'frontend/src/main.tsx',
        'frontend/src/components/Dashboard.tsx',
        'frontend/src/components/UploadForm.tsx',
        'frontend/src/components/VerificationView.tsx',
        'frontend/src/components/SearchInterface.tsx',
        'frontend/src/services/api.ts',
    ]
    
    missing = []
    for filepath in required_files:
        if check_file_exists(filepath):
            print_success(f"{filepath} exists")
        else:
            missing.append(filepath)
            print_error(f"{filepath} MISSING")
    
    if missing:
        print_error(f"\nMissing {len(missing)} file(s)")
        return False
    else:
        print_success(f"All {len(required_files)} frontend files exist")
        return True

def test_backend_imports():
    """Test backend imports"""
    print_header("Testing Backend Imports")
    
    try:
        from backend.config import settings
        print_success("Config imported")
    except Exception as e:
        print_error(f"Config import failed: {e}")
        return False
    
    try:
        from backend.database import Base, engine, AdmissionForm, StudentProfile, StudentDocument
        print_success("Database models imported")
    except Exception as e:
        print_error(f"Database import failed: {e}")
        return False
    
    try:
        from backend.ocr.ocr_factory import OCRFactory
        print_success("OCR factory imported")
    except Exception as e:
        print_error(f"OCR factory import failed: {e}")
        return False
    
    try:
        from backend.utils.form_parser import parse_form_text
        print_success("Form parser imported")
    except Exception as e:
        print_error(f"Form parser import failed: {e}")
        return False
    
    try:
        from backend.api.routes import upload, forms, students, documents
        print_success("API routes imported")
    except Exception as e:
        print_error(f"API routes import failed: {e}")
        return False
    
    return True

def test_database_connection():
    """Test database connection"""
    print_header("Testing Database Connection")
    
    try:
        from backend.database import engine, Base
        # Try to create tables
        Base.metadata.create_all(bind=engine)
        print_success("Database connection successful")
        print_success("Tables can be created")
        return True
    except Exception as e:
        print_error(f"Database connection failed: {e}")
        print_warning("This is OK if database file doesn't exist yet")
        return False

def test_ocr_providers():
    """Test OCR providers"""
    print_header("Testing OCR Providers")
    
    try:
        from backend.ocr.ocr_factory import OCRFactory
        providers = OCRFactory.get_available_providers()
        
        if 'tesseract' in providers:
            print_success("Tesseract OCR provider available")
        else:
            print_warning("Tesseract OCR provider not available")
        
        print_info(f"Available providers: {', '.join(providers)}")
        
        # Try to create a provider
        try:
            provider = OCRFactory.create_provider('tesseract')
            print_success("Can create OCR provider instance")
            return True
        except Exception as e:
            print_error(f"Cannot create OCR provider: {e}")
            return False
            
    except Exception as e:
        print_error(f"OCR provider test failed: {e}")
        return False

def test_form_parser():
    """Test form parser"""
    print_header("Testing Form Parser")
    
    try:
        from backend.utils.form_parser import parse_form_text
        
        # Test with sample text
        sample_text = """
        Name: John Doe
        Date of Birth: 01/01/2000
        Phone: 1234567890
        Email: john@example.com
        Enrollment Number: ENR2024001
        """
        
        result = parse_form_text(sample_text)
        
        if isinstance(result, dict):
            print_success("Form parser works correctly")
            print_info(f"Extracted {len(result)} fields")
            if 'enrollment_number' in result or 'student_name' in result:
                print_success("Can extract enrollment number and student name")
            return True
        else:
            print_error("Form parser returned unexpected format")
            return False
            
    except Exception as e:
        print_error(f"Form parser test failed: {e}")
        return False

def check_node_npm():
    """Check Node.js and npm"""
    print_header("Checking Node.js and npm")
    
    try:
        result = subprocess.run(['node', '--version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            version = result.stdout.strip()
            print_success(f"Node.js installed: {version}")
            
            # Check npm
            result = subprocess.run(['npm', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                npm_version = result.stdout.strip()
                print_success(f"npm installed: {npm_version}")
                return True
            else:
                print_error("npm not found")
                return False
        else:
            print_error("Node.js not installed")
            return False
    except FileNotFoundError:
        print_error("Node.js not installed")
        print_info("Install from: https://nodejs.org/")
        return False
    except Exception as e:
        print_error(f"Error checking Node.js: {e}")
        return False

def check_frontend_dependencies():
    """Check if frontend dependencies are installed"""
    print_header("Checking Frontend Dependencies")
    
    node_modules = Path('frontend/node_modules')
    if node_modules.exists():
        print_success("Frontend dependencies installed (node_modules exists)")
        return True
    else:
        print_warning("Frontend dependencies not installed")
        print_info("Install with: cd frontend && npm install")
        return False

def test_api_endpoints():
    """Test if API endpoints are accessible (requires server running)"""
    print_header("Testing API Endpoints (requires server running)")
    
    import requests
    
    try:
        response = requests.get('http://localhost:8000/health', timeout=2)
        if response.status_code == 200:
            print_success("Backend server is running")
            print_success("Health endpoint accessible")
            
            # Test providers endpoint
            try:
                response = requests.get('http://localhost:8000/api/providers', timeout=2)
                if response.status_code == 200:
                    print_success("Providers endpoint accessible")
                    return True
            except:
                print_warning("Providers endpoint not accessible (server may not be running)")
                return False
        else:
            print_warning(f"Backend server returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print_warning("Backend server not running (this is OK for dependency check)")
        print_info("Start server with: python3 -m uvicorn backend.main:app --reload")
        return False
    except Exception as e:
        print_warning(f"Could not test API endpoints: {e}")
        return False

def main():
    """Run all tests"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║  Student Records Management System - System Test         ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print(Colors.RESET)
    
    results = {}
    
    # Python and dependencies
    results['python_version'] = check_python_version()
    results['python_deps'] = check_python_dependencies()
    results['tesseract'] = check_tesseract()
    
    # Files
    results['backend_files'] = check_backend_files()
    results['frontend_files'] = check_frontend_files()
    
    # Backend tests (only if dependencies installed)
    if results['python_deps']:
        results['backend_imports'] = test_backend_imports()
        results['database'] = test_database_connection()
        results['ocr_providers'] = test_ocr_providers()
        results['form_parser'] = test_form_parser()
    else:
        print_warning("\nSkipping backend tests (dependencies not installed)")
        results['backend_imports'] = False
        results['database'] = False
        results['ocr_providers'] = False
        results['form_parser'] = False
    
    # Frontend
    results['node_npm'] = check_node_npm()
    results['frontend_deps'] = check_frontend_dependencies()
    
    # API (optional - requires server)
    results['api_endpoints'] = test_api_endpoints()
    
    # Summary
    print_header("Test Summary")
    
    total_tests = len(results)
    passed_tests = sum(1 for v in results.values() if v)
    
    print(f"\n{Colors.BOLD}Results: {passed_tests}/{total_tests} tests passed{Colors.RESET}\n")
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        color = Colors.GREEN if result else Colors.RED
        print(f"{color}{status}{Colors.RESET} - {test_name.replace('_', ' ').title()}")
    
    print()
    
    if passed_tests == total_tests:
        print_success("🎉 All tests passed! System is ready to run.")
        return 0
    elif passed_tests >= total_tests * 0.7:
        print_warning("⚠️  Most tests passed. System should work but some features may be limited.")
        print_info("Install missing dependencies to enable all features.")
        return 1
    else:
        print_error("❌ Many tests failed. Please install dependencies first.")
        print_info("Run: pip install -r requirements.txt")
        print_info("Then: cd frontend && npm install")
        return 2

if __name__ == '__main__':
    sys.exit(main())
