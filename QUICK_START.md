# Quick Start Guide

Get your Student Records Management System up and running in minutes!

## Prerequisites

- Python 3.8 or higher
- Node.js 16 or higher
- Tesseract OCR (for free OCR)

## Installation Steps

### 1. Install Tesseract OCR

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
```

**macOS:**
```bash
brew install tesseract
```

**Windows:**
Download and install from: https://github.com/UB-Mannheim/tesseract/wiki

### 2. Install Python Dependencies

```bash
# From project root
pip install -r requirements.txt
```

### 3. Install Frontend Dependencies

```bash
cd frontend
npm install
cd ..
```

### 4. Initialize Database

The database will be created automatically on first run. No manual setup needed!

### 5. Start the Backend Server

```bash
# From project root
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at: http://localhost:8000

API docs: http://localhost:8000/docs

### 6. Start the Frontend

Open a new terminal:

```bash
cd frontend
npm run dev
```

Frontend will be available at: http://localhost:5173

## First Steps

1. **Open the app** at http://localhost:5173
2. **Upload a test form:**
   - Click "Upload" in the navigation
   - Choose a scanned form (PDF, JPG, or PNG)
   - Select "Tesseract" as OCR provider
   - Click "Upload Form"
3. **Verify the data:**
   - Review extracted text
   - Correct any errors
   - Click "Save & Verify"
4. **Search and export:**
   - Go to "Search" page
   - Enter search criteria
   - Export to CSV or JSON

## Using Better OCR (Optional)

For handwritten forms, use cloud OCR providers:

### Google Document AI (BEST for handwriting)

1. Create Google Cloud account
2. Enable Document AI API
3. Create service account and download JSON key
4. Create `.env` file:

```env
GOOGLE_DOCUMENT_AI_PROJECT_ID=your-project-id
GOOGLE_DOCUMENT_AI_LOCATION=us
GOOGLE_DOCUMENT_AI_PROCESSOR_ID=your-processor-id
GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
OCR_PROVIDER=google-documentai
```

5. Install package:
```bash
pip install google-cloud-documentai==2.20.0
```

6. Restart backend server

See [SETUP_OCR.md](SETUP_OCR.md) for detailed instructions.

## Troubleshooting

**Backend won't start:**
- Check Python version: `python --version` (should be 3.8+)
- Reinstall dependencies: `pip install -r requirements.txt`

**Frontend won't start:**
- Check Node version: `node --version` (should be 16+)
- Delete `node_modules` and run `npm install` again

**OCR not working:**
- For Tesseract: Check installation with `tesseract --version`
- For cloud providers: Verify API credentials in `.env` file

**Cannot connect to backend:**
- Verify backend is running on port 8000
- Check firewall settings
- Try accessing http://localhost:8000/health

## What's Next?

- Read the [USER_GUIDE.md](USER_GUIDE.md) for detailed usage instructions
- Configure cloud OCR providers for better accuracy ([SETUP_OCR.md](SETUP_OCR.md))
- Review [SYSTEM_OVERVIEW.md](SYSTEM_OVERVIEW.md) for architecture details

## Support

For issues or questions:
- Check the [USER_GUIDE.md](USER_GUIDE.md)
- Review API documentation at http://localhost:8000/docs
- Check GitHub issues or contact your administrator

---

**You're all set!** Start digitizing those admission forms! 📝✨
