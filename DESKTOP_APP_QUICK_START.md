# Desktop App Quick Start Guide

## ✅ Installation

1. **Run the installer**: `electron\dist\OCR Form Extractor Setup 1.0.0.exe`
2. Follow the installation wizard
3. Launch the app from the Start Menu or desktop shortcut

## 🔧 What Was Fixed

### Backend Startup
- Created `backend/run_server.py` wrapper that properly starts uvicorn
- Backend now runs as a standalone executable
- Environment variables set automatically for desktop mode

### Error Handling
- Improved error messages with detailed information
- Log file created at: `%APPDATA%\ocr-admission-forms-desktop\app.log`
- DevTools accessible with `Ctrl+Shift+I` for debugging

### Frontend Loading
- Fixed CORS to allow `file://` protocol for Electron
- Frontend loads from bundled files
- API connection configured automatically

## 🐛 Troubleshooting

### If the app shows a blank window:

1. **Press `Ctrl+Shift+I`** to open DevTools and see errors
2. **Check the log file**: `%APPDATA%\ocr-admission-forms-desktop\app.log`
3. **Verify files are installed**:
   - `resources/backend/api.exe` should exist
   - `resources/frontend/index.html` should exist
   - `resources/data/.env` should exist
   - `resources/data/google-cloud-credentials.json` should exist

### Common Issues:

#### Backend Not Starting
- **Check port 8000**: Make sure no other app is using it
- **Check log file**: Look for backend error messages
- **Test backend manually**: Run `resources/backend/api.exe` from command line

#### Frontend Not Loading
- **Check DevTools console**: Press `Ctrl+Shift+I` and look for errors
- **Verify frontend files**: Check that `resources/frontend/index.html` exists

#### API Connection Errors
- **Backend must be running**: Check if backend started successfully
- **CORS issues**: Should be fixed, but check DevTools Network tab

## 📁 Installed App Structure

After installation, the app is located at:
```
C:\Program Files\OCR Form Extractor\ (or your chosen location)
├── OCR Form Extractor.exe
└── resources/
    ├── app.asar (Electron app code)
    ├── backend/
    │   └── api.exe (Python backend)
    ├── frontend/
    │   ├── index.html
    │   └── assets/
    └── data/
        ├── .env
        ├── google-cloud-credentials.json
        └── admission_forms.db
```

## 🔍 Debugging

### Enable DevTools
- Press `Ctrl+Shift+I` in the app window
- Or set environment variable: `SHOW_DEVTOOLS=1` before launching

### View Logs
- Log file: `%APPDATA%\ocr-admission-forms-desktop\app.log`
- Backend console: Run `api.exe` manually to see output

### Test Backend Manually
1. Navigate to installation directory
2. Go to `resources/backend/`
3. Run `api.exe` from command line
4. Check if it starts on `http://localhost:8000`

## ✅ Success Indicators

The app is working correctly when:
1. Window opens without error messages
2. Frontend UI loads (you see the OCR form interface)
3. Backend API responds (check DevTools Network tab)
4. No errors in console (DevTools)

## 🚀 Next Steps

1. **Test the app**: Upload a form and verify OCR works
2. **Check logs**: Monitor `app.log` for any issues
3. **Report issues**: Include log file contents when reporting problems

## 📝 Notes

- The backend runs on `http://localhost:8000`
- The frontend loads from bundled files (no dev server needed)
- All configuration files are in `resources/data/`
- Database is created automatically if it doesn't exist
