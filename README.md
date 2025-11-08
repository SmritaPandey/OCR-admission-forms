# Student Admission Form Digitization System

A comprehensive software system for digitizing handwritten student admission forms using advanced OCR (Optical Character Recognition) technology. The system allows scanned handwritten forms to be uploaded, automatically extracts text using state-of-the-art OCR, and presents the data for manual verification and correction. Verified data is stored in a secure database and can be searched, filtered, and exported via an intuitive user interface.

## ✨ Key Features

- **📤 Smart File Upload**: Upload scanned admission forms in multiple formats (JPG, PNG, PDF, TIFF, BMP)
- **🤖 Advanced OCR**: Automatic text extraction using multiple world-class OCR providers:
  - **Google Document AI** ⭐ (BEST for handwritten forms)
  - **Azure Form Recognizer** ⭐ (BEST for structured forms with checkboxes)
  - **AWS Textract** (Excellent for forms and tables)
  - **Google Cloud Vision** (Good for general text)
  - **Tesseract** (Free, good for printed text)
- **✅ Intelligent Verification**: Side-by-side view with auto-fill capabilities
- **📋 Comprehensive Form Fields**: 40+ fields covering all student information
- **🔍 Powerful Search**: Search by name, enrollment number, phone, email, or any field
- **📎 Document Management**: Attach supporting documents (ID, certificates, etc.)
- **🎓 Student Profiles**: Automatic linking of forms and documents
- **📊 Data Export**: Export to CSV or JSON with filtering
- **🔄 Re-extraction**: Try different OCR providers for better results
- **📱 Responsive Design**: Works on desktop and tablets

## System Architecture

### Backend (FastAPI)
- **Framework**: FastAPI (Python)
- **Database**: SQLite (default) or PostgreSQL
- **ORM**: SQLAlchemy
- **OCR**: Multi-provider OCR support via factory pattern

### Frontend (React + TypeScript)
- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite
- **Routing**: React Router
- **HTTP Client**: Axios

## 📋 Prerequisites

### Required
- **Python 3.8+** with pip
- **Node.js 16+** with npm
- **Tesseract OCR** (for free OCR option)

### Recommended for Best Handwriting Recognition
- **Google Cloud Document AI** (Best accuracy for handwriting) - See [SETUP_OCR.md](SETUP_OCR.md)
- **Azure Form Recognizer** (Best for structured forms) - See [SETUP_OCR.md](SETUP_OCR.md)
- **AWS Textract** (Good for forms and tables) - See [SETUP_OCR.md](SETUP_OCR.md)

### Optional
- PostgreSQL (for production deployments)

## 🚀 Quick Start

**Want to get started quickly?** See [QUICK_START.md](QUICK_START.md) for a 5-minute setup guide!

## 📦 Full Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd "Admission Form OCR"
```

### 2. Backend Setup

#### Install Python Dependencies

```bash
cd backend
pip install -r ../requirements.txt
```

Or install manually:
```bash
pip install fastapi uvicorn sqlalchemy pydantic pydantic-settings pillow pytesseract python-multipart
```

#### Install Tesseract OCR

**Windows:**
1. Download from: https://github.com/UB-Mannheim/tesseract/wiki
2. Install and add to PATH, or set `TESSDATA_PREFIX` environment variable

**macOS:**
```bash
brew install tesseract
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install tesseract-ocr
```

### 3. Frontend Setup

```bash
cd frontend
npm install
```

### 4. Configuration

Create a `.env` file in the root directory (optional - defaults work for SQLite):

```env
# Database (defaults to SQLite)
DATABASE_URL=sqlite:///./admission_forms.db

# For PostgreSQL:
# DATABASE_URL=postgresql://postgres:postgres@localhost:5432/admission_forms

# OCR Provider
OCR_PROVIDER=tesseract

# Optional: Google Cloud Vision
# GOOGLE_CLOUD_API_KEY=your-key
# GOOGLE_CLOUD_PROJECT_ID=your-project-id

# Optional: Azure Vision
# AZURE_VISION_KEY=your-key
# AZURE_VISION_ENDPOINT=https://your-endpoint.cognitiveservices.azure.com/

# CORS Origins
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

## Running the Application

### Start Backend Server

From the project root:

```bash
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Or from the backend directory:

```bash
cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The backend API will be available at: `http://localhost:8000`

API documentation (Swagger UI): `http://localhost:8000/docs`

### Start Frontend Development Server

From the frontend directory:

```bash
cd frontend
npm run dev
```

The frontend will be available at: `http://localhost:5173` (or the port shown in terminal)

## Usage

### 1. Upload a Form

1. Navigate to the **Upload** page
2. Click "Choose File" and select a scanned admission form
3. Optionally select an OCR provider (default: Tesseract)
4. Click "Upload Form"
5. The system will automatically extract text from the form

### 2. Verify Form Data

1. From the Dashboard, click "View" on an extracted form
2. Review the extracted text in the "Extracted Text (Raw)" section
3. Fill in or correct the form fields:
   - Student Name (required)
   - Date of Birth
   - Address
   - Phone Number
   - Email
   - Guardian Name
   - Guardian Phone
   - Course Applied
   - Previous Qualification
4. Click "Save & Verify" to save the verified data

### 3. Search Forms

1. Navigate to the **Search** page
2. Enter search criteria (name, phone, email, course, or status)
3. Click "Search" to find matching forms

### 4. Export Data

1. From the Dashboard or Search results, use the export functionality
2. Choose CSV or JSON format
3. Download the exported file

### 5. Re-extract with Different OCR Provider

1. Open a form for verification
2. Click "Re-extract"
3. Optionally select a different OCR provider
4. Review the new extraction results

## API Endpoints

### Upload
- `POST /api/upload` - Upload a form and extract text
- `GET /api/providers` - List available OCR providers

### Forms
- `GET /api/forms/` - List all forms (with pagination)
- `GET /api/forms/{id}` - Get form details
- `POST /api/forms/{id}/extract` - Re-extract form
- `PUT /api/forms/{id}/verify` - Verify and save form data
- `GET /api/forms/search/results` - Search forms
- `DELETE /api/forms/{id}` - Delete a form

### Export
- `GET /api/forms/export` - Export forms (CSV/JSON)

### Health Check
- `GET /health` - Server health status
- `GET /` - API root

## Database Schema

### AdmissionForm Table

- `id` - Primary key
- `filename` - Original filename
- `file_path` - Path to uploaded file
- `upload_date` - Upload timestamp
- `ocr_provider` - OCR provider used
- `status` - Current status (uploaded, extracting, extracted, verified, error)
- `extracted_data` - JSON with OCR results (raw_text, confidence, etc.)
- `student_name` - Verified student name
- `date_of_birth` - Date of birth
- `address` - Address
- `phone_number` - Phone number
- `email` - Email address
- `guardian_name` - Guardian name
- `guardian_phone` - Guardian phone
- `course_applied` - Course applied for
- `previous_qualification` - Previous qualification
- `additional_info` - Additional flexible fields (JSON)
- `verified_date` - Verification timestamp
- `verified_by` - User who verified (optional)

## Configuration Options

### Database
- **SQLite** (default): No setup required, file-based database
- **PostgreSQL**: Requires PostgreSQL server, update `DATABASE_URL` in config

### OCR Providers

#### Tesseract (Default)
- Free and open-source
- Requires Tesseract installation
- Good for printed text, moderate accuracy for handwriting

#### Google Cloud Vision
- High accuracy, especially for handwriting
- Requires API key and project ID
- Paid service (with free tier)

#### Azure Computer Vision
- Good accuracy for various document types
- Requires API key and endpoint
- Paid service (with free tier)

#### ABBYY FineReader
- Professional-grade OCR
- Requires ABBYY FineReader Server
- Commercial license required

## Development

### Project Structure

```
.
├── backend/
│   ├── api/
│   │   ├── routes/        # API route handlers
│   │   └── dependencies.py
│   ├── models/           # Pydantic models
│   ├── ocr/              # OCR provider implementations
│   ├── utils/             # Utility functions
│   ├── config.py          # Configuration settings
│   ├── database.py        # Database models and setup
│   └── main.py            # FastAPI application
├── frontend/
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── services/      # API service layer
│   │   └── App.tsx        # Main app component
│   └── package.json
├── requirements.txt       # Python dependencies
└── README.md
```

## 📚 Documentation

- **[QUICK_START.md](QUICK_START.md)** - Get started in 5 minutes
- **[USER_GUIDE.md](USER_GUIDE.md)** - Complete user guide with screenshots and best practices
- **[SETUP_OCR.md](SETUP_OCR.md)** - Detailed OCR provider setup (Google, Azure, AWS)
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Production deployment guide
- **[SYSTEM_OVERVIEW.md](SYSTEM_OVERVIEW.md)** - Technical architecture and design

## 🎯 System Capabilities

### Form Fields Supported

The system can extract and manage 40+ fields including:

- **Basic Details**: Name, DOB, Gender, Category, Nationality, Religion, Aadhar, Blood Group
- **Address**: Permanent and Correspondence addresses with City, State, Pincode
- **Contact**: Phone, Alternate Phone, Email, Emergency Contacts
- **Parent/Guardian**: Father, Mother, Guardian details with occupation and contact
- **Education**: 10th and 12th details (Board, Year, %, School), Previous Qualifications
- **Admission**: Course Applied, Application Number, Enrollment Number, Admission Date
- **Documents**: ID Proof, Academic Certificates, Medical, Birth, Income, Caste Certificates

### OCR Provider Comparison

| Provider | Handwriting | Forms | Checkboxes | Cost | Setup |
|----------|------------|-------|------------|------|-------|
| Google Document AI | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ✅ | $$ | Medium |
| Azure Form Recognizer | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ✅ | $$ | Medium |
| AWS Textract | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ✅ | $$ | Medium |
| Google Vision | ⭐⭐⭐⭐ | ⭐⭐⭐ | ❌ | $$ | Easy |
| Tesseract | ⭐⭐⭐ | ⭐⭐⭐ | ❌ | FREE | Easy |

### Search and Filter Options

- Search by: Student Name, Enrollment Number, Application Number, Phone, Email, Course
- Filter by: Status (Uploaded, Extracted, Verified, Error)
- Sort by: Upload Date, Verification Date, Student Name
- Export: Filtered results to CSV or JSON

## 🔧 Troubleshooting

For common issues and solutions, see:
- [USER_GUIDE.md - Troubleshooting Section](USER_GUIDE.md#troubleshooting)
- [DEPLOYMENT.md - Production Issues](DEPLOYMENT.md#troubleshooting-production-issues)

### Quick Fixes

**Backend won't start:**
```bash
pip install -r requirements.txt
python -m uvicorn backend.main:app --reload
```

**Frontend won't start:**
```bash
cd frontend
npm install
npm run dev
```

**OCR not working:**
- Check Tesseract: `tesseract --version`
- Verify API credentials in `.env` file
- See [SETUP_OCR.md](SETUP_OCR.md) for detailed configuration

## Security Considerations

- File uploads are validated by extension and size
- CORS is configured to restrict origins
- Database credentials should be stored in `.env` (not committed)
- In production, use:
  - HTTPS
  - Authentication/authorization
  - Rate limiting
  - File scanning for malware
  - Secure file storage

## License

[Specify your license here]

## Support

For issues, questions, or contributions, please [open an issue] or [contact the development team].

