# Student Admission Form Digitization System

A comprehensive software system for digitizing student admission forms using OCR (Optical Character Recognition) technology. The system allows scanned handwritten forms to be uploaded, automatically extracts text using OCR, and presents the data for manual verification and correction. Verified data is stored in a secure database and can be searched or exported via an intuitive user interface.

## Features

- **File Upload**: Upload scanned admission forms in multiple formats (JPG, PNG, PDF, TIFF, BMP)
- **OCR Extraction**: Automatic text extraction using multiple OCR providers:
  - Tesseract (default, open-source)
  - Google Cloud Vision (optional)
  - Azure Computer Vision (optional)
  - ABBYY FineReader (optional)
- **Manual Verification**: User-friendly interface for verifying and correcting extracted data
- **Search & Filter**: Search forms by student name, phone number, email, course, or status
- **Data Export**: Export verified forms to CSV or JSON format
- **Dashboard**: Overview of all forms with status tracking
- **Re-extraction**: Re-extract forms with different OCR providers if needed

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

## Prerequisites

### Required
- **Python 3.8+** with pip
- **Node.js 16+** with npm (for frontend)
- **Tesseract OCR** (for default OCR provider)

### Optional
- PostgreSQL (if not using SQLite)
- Google Cloud Vision API credentials
- Azure Computer Vision credentials
- ABBYY FineReader Server

## Installation

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

## Troubleshooting

### Backend Issues

**Database Connection Error:**
- SQLite: Ensure write permissions in the project directory
- PostgreSQL: Verify PostgreSQL is running and credentials are correct

**OCR Not Working:**
- Tesseract: Verify Tesseract is installed and in PATH
- Other providers: Check API credentials in `.env` file

**Import Errors:**
- Ensure all Python dependencies are installed: `pip install -r requirements.txt`

### Frontend Issues

**Cannot Connect to Backend:**
- Verify backend is running on port 8000
- Check CORS settings in `backend/config.py`
- Verify `VITE_API_BASE_URL` in frontend (defaults to `http://localhost:8000`)

**File Upload Fails:**
- Check file size (max 10MB default)
- Verify file format is allowed (jpg, jpeg, png, pdf, tiff, bmp)
- Check backend logs for detailed error messages

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

