# Desktop App Troubleshooting Guide

## If the app shows a blank/error window:

### 1. Check the Log File
The app creates a log file at:
- Windows: `%APPDATA%\ocr-admission-forms-desktop\app.log`
- Or check the console output when running the installed app

### 2. Common Issues

#### Backend Not Starting
- **Symptom**: Blank window or "Failed to start backend" error
- **Solution**: 
  - Check if port 8000 is already in use
  - Verify `api.exe` exists in the installed app's resources
  - Check that `.env` and `google-cloud-credentials.json` are in the data folder

#### Frontend Not Loading
- **Symptom**: Blank window or "Frontend Not Found" error
- **Solution**:
  - Verify `frontend/index.html` exists in the installed app's resources
  - Check browser console (F12) for errors

#### API Connection Issues
- **Symptom**: Frontend loads but shows connection errors
- **Solution**:
  - Ensure backend is running on `http://localhost:8000`
  - Check CORS settings in backend config
  - Verify API_BASE_URL is set correctly

### 3. Manual Testing

#### Test Backend Directly
1. Navigate to the installed app directory
2. Find `resources/backend/api.exe`
3. Run it manually to see error messages
4. Check if it starts on port 8000

#### Test Frontend
1. Open `resources/frontend/index.html` in a browser
2. Check browser console for errors
3. Verify API calls work

### 4. Rebuild Steps

If issues persist:
1. Delete `backend-dist` folder
2. Delete `frontend/dist` folder  
3. Delete `electron/dist` folder
4. Run `build_desktop.bat` again

### 5. Environment Variables

The desktop app sets these automatically:
- `DESKTOP_APP=1` - Tells backend it's in desktop mode
- `DATA_DIR` - Points to resources/data folder
- `PORT=8000` - Backend port
- `HOST=127.0.0.1` - Backend host

### 6. File Structure (After Installation)

```
OCR Form Extractor/
├── OCR Form Extractor.exe
└── resources/
    ├── app.asar (Electron app)
    ├── backend/
    │   └── api.exe
    ├── frontend/
    │   ├── index.html
    │   └── assets/
    └── data/
        ├── .env
        ├── google-cloud-credentials.json
        └── admission_forms.db
```

### 7. Getting Help

If the app still doesn't work:
1. Check the log file: `%APPDATA%\ocr-admission-forms-desktop\app.log`
2. Run the app from command line to see console output
3. Check Windows Event Viewer for errors
4. Verify all files are present in the installation directory
