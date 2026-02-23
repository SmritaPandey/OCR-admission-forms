# Testing and Running the System Locally

This guide explains how to test and run the Student Records Management System locally.

## Quick Start

### Option 1: Automated Setup (Recommended)

```bash
# 1. Run setup script (installs all dependencies)
./setup_local.sh

# 2. Test the system
python3 test_system.py

# 3. Run the system
./run_local.sh
```

### Option 2: Manual Setup

```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Install Tesseract OCR
sudo apt-get install tesseract-ocr  # Ubuntu/Debian
# OR
brew install tesseract  # macOS

# 3. Install frontend dependencies
cd frontend
npm install
cd ..

# 4. Test the system
python3 test_system.py

# 5. Start backend (Terminal 1)
python3 -m uvicorn backend.main:app --reload --port 8000

# 6. Start frontend (Terminal 2)
cd frontend
npm run dev
```

---

## Test Script

The `test_system.py` script checks:

### ✅ What It Tests

1. **Python Version** - Verifies Python 3.8+
2. **Python Dependencies** - Checks all required packages
3. **Tesseract OCR** - Verifies OCR installation
4. **Backend Files** - Checks all code files exist
5. **Frontend Files** - Checks all UI files exist
6. **Backend Imports** - Tests Python module imports
7. **Database Connection** - Tests database setup
8. **OCR Providers** - Tests OCR factory
9. **Form Parser** - Tests form text parsing
10. **Node.js/npm** - Checks Node.js installation
11. **Frontend Dependencies** - Checks npm packages
12. **API Endpoints** - Tests server endpoints (if running)

### Usage

```bash
# Run all tests
python3 test_system.py

# Expected output:
# ✅ Python 3.12.x (Required: 3.8+)
# ✅ FastAPI installed
# ✅ SQLAlchemy installed
# ... etc
```

---

## Pytest Unit Suite

In addition to the system smoke test, targeted unit tests cover form search filters and export helpers.

```bash
# Run backend/unit test suite
pytest tests/test_filters_and_export.py
```

These tests validate:

- Search filtering across name, status, and upload date ranges
- Export serialization logic for CSV and JSON payloads
- Inclusion of newly added fields (enrollment numbers, metadata) in exports

### Test Results

- **All Pass (100%)**: System is ready to run
- **Most Pass (70%+)**: System should work, some features may be limited
- **Many Fail (<70%)**: Install dependencies first

---

## Run Scripts

### Linux/macOS: `run_local.sh`

```bash
# Make executable (first time only)
chmod +x run_local.sh

# Run the system
./run_local.sh
```

**What it does:**
- Checks Python, Node.js, npm
- Checks if dependencies are installed
- Offers to install missing dependencies
- Starts backend on port 8000
- Starts frontend on port 5173
- Shows URLs and logs

**Features:**
- Auto-installs dependencies if missing
- Checks if ports are in use
- Graceful shutdown on Ctrl+C
- Separate log files (backend.log, frontend.log)

### Windows: `run_local.bat`

```batch
# Double-click or run from command prompt
run_local.bat
```

**What it does:**
- Same as Linux script but for Windows
- Opens separate windows for backend and frontend
- Easy to stop (just close the windows)

---

## Manual Testing

### 1. Test Backend Only

```bash
# Start backend
python3 -m uvicorn backend.main:app --reload --port 8000

# In another terminal, test endpoints
curl http://localhost:8000/health
curl http://localhost:8000/api/providers
```

### 2. Test Frontend Only

```bash
# Start frontend
cd frontend
npm run dev

# Open browser
# http://localhost:5173
```

### 3. Test Database

```python
# Python shell
python3
>>> from backend.database import Base, engine
>>> Base.metadata.create_all(bind=engine)
>>> print("Database tables created!")
```

### 4. Test OCR

```python
# Python shell
python3
>>> from backend.ocr.ocr_factory import OCRFactory
>>> providers = OCRFactory.get_available_providers()
>>> print(f"Available: {providers}")
>>> provider = OCRFactory.create_provider('tesseract')
>>> print("OCR provider created successfully!")
```

### 5. Test Form Parser

```python
# Python shell
python3
>>> from backend.utils.form_parser import parse_form_text
>>> text = "Name: John Doe\nEnrollment Number: ENR2024001\nPhone: 1234567890"
>>> result = parse_form_text(text)
>>> print(result)
```

---

## Troubleshooting Tests

### Test Script Issues

**Problem: "ModuleNotFoundError"**
```bash
# Solution: Install dependencies
pip install -r requirements.txt
```

**Problem: "Tesseract not found"**
```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# macOS
brew install tesseract

# Windows
# Download from: https://github.com/UB-Mannheim/tesseract/wiki
```

**Problem: "Node.js not found"**
```bash
# Install Node.js from: https://nodejs.org/
# Then run:
cd frontend
npm install
```

### Run Script Issues

**Problem: "Port 8000 already in use"**
```bash
# Find and kill process
lsof -ti:8000 | xargs kill -9

# OR change port in run script
```

**Problem: "Backend failed to start"**
```bash
# Check backend.log for errors
cat backend.log

# Common issues:
# - Missing dependencies: pip install -r requirements.txt
# - Database error: Check DATABASE_URL in .env
# - Port conflict: Change port or kill existing process
```

**Problem: "Frontend failed to start"**
```bash
# Check frontend.log for errors
cat frontend.log

# Common issues:
# - Missing dependencies: cd frontend && npm install
# - Port conflict: Change port in vite.config.ts
```

---

## Testing Checklist

Before deploying to production:

- [ ] All test script tests pass
- [ ] Backend starts without errors
- [ ] Frontend starts without errors
- [ ] Can upload a test form
- [ ] OCR extraction works
- [ ] Form fields auto-fill correctly
- [ ] Can save verified form
- [ ] Can search by enrollment number
- [ ] Can search by name
- [ ] Can upload documents
- [ ] Can export to CSV
- [ ] Can export to JSON
- [ ] Multi-page PDFs work
- [ ] Re-extraction works

---

## Performance Testing

### Test Upload Speed

```bash
# Upload a test form and measure time
time curl -X POST http://localhost:8000/api/upload \
  -F "file=@test_form.pdf" \
  -F "ocr_provider=tesseract"
```

### Test Search Speed

```bash
# Test search endpoint
time curl "http://localhost:8000/api/forms/search/results?student_name=John"
```

### Load Testing

```bash
# Install Apache Bench
sudo apt-get install apache2-utils

# Test backend health endpoint
ab -n 100 -c 10 http://localhost:8000/health
```

---

## Continuous Testing

### Watch Mode (Auto-restart on changes)

Backend already has `--reload` flag:
```bash
python3 -m uvicorn backend.main:app --reload
```

Frontend Vite has hot reload by default:
```bash
cd frontend
npm run dev
```

---

## Test Data

### Sample Form Text for Testing

```python
sample_text = """
SRCC DATA FORM

Name: John Doe
Date of Birth: 01/01/2000
Gender: Male
Category: General
Nationality: Indian
Aadhar Number: 1234 5678 9012
Phone Number: 9876543210
Email: john.doe@example.com
Enrollment Number: ENR2024001
Application Number: APP2024001
Course Applied: B.Com (Hons)
Permanent Address: 123 Main Street, New Delhi
City: New Delhi
State: Delhi
Pincode: 110001
Father Name: Robert Doe
Mother Name: Jane Doe
10th Percentage: 85.5
12th Percentage: 88.0
"""
```

---

## Next Steps

After testing:

1. **Configure OCR Provider** - See [SETUP_OCR.md](SETUP_OCR.md)
2. **Set Up Production** - See [DEPLOYMENT.md](DEPLOYMENT.md)
3. **Read User Guide** - See [USER_GUIDE.md](USER_GUIDE.md)

---

## Support

If tests fail:

1. Check error messages in test output
2. Review log files (backend.log, frontend.log)
3. Verify all dependencies are installed
4. Check system requirements (Python 3.8+, Node.js 16+)
5. Review [TROUBLESHOOTING.md](USER_GUIDE.md#troubleshooting) section

For more help, see the main [README.md](README.md).
