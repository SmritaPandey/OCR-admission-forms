# Electron Desktop App Build Guide

## Overview

This guide explains how to build the OCR Admission Forms desktop application using Electron.

## Prerequisites

1. **Python 3.8+** - For backend
2. **Node.js 18+** - For frontend and Electron
3. **PyInstaller** - For packaging Python backend
4. **Electron Builder** - For packaging Electron app

## Build Steps

### Windows

Run the automated build script:
```bash
build_desktop.bat
```

Or build manually:

1. **Build Backend:**
   ```bash
   pip install -r requirements.txt
   pip install pyinstaller
   pyinstaller --clean build_backend.spec
   copy dist\api.exe backend-dist\api.exe
   ```

2. **Build Frontend:**
   ```bash
   cd frontend
   npm install
   npm run build
   cd ..
   ```

3. **Build Electron App:**
   ```bash
   cd electron
   npm install
   npm run dist
   cd ..
   ```

The installer will be in `electron/dist/`

### Linux/Mac

Run the automated build script:
```bash
chmod +x build_desktop.sh
./build_desktop.sh
```

Or follow the same manual steps as Windows (use `cp` instead of `copy`).

## Build Configuration

### Backend (PyInstaller)

- **Spec file:** `build_backend.spec`
- **Output:** `backend-dist/api.exe` (Windows) or `backend-dist/api` (Linux/Mac)
- **Includes:** All Python dependencies, FastAPI, OCR providers

### Frontend (Vite)

- **Config:** `frontend/vite.config.ts`
- **Output:** `frontend/dist/`
- **Base path:** `./` (relative for Electron)

### Electron (electron-builder)

- **Config:** `electron/package.json` → `build` section
- **Output:** Installer in `electron/dist/`
- **Platforms:** Windows (NSIS), Mac (DMG), Linux (AppImage)

## File Structure in Build

```
electron/dist/
├── OCR Form Extractor Setup X.X.X.exe  (Windows installer)
└── ...

Resources (bundled):
├── backend/
│   └── api.exe
├── frontend/
│   ├── index.html
│   ├── assets/
│   └── ...
└── data/
    └── (initial data files)
```

## Environment Variables

The app uses `AppData/Roaming/OCR Form Extractor/` for:
- Database files
- Configuration (.env)
- Logs
- Uploaded files

## Troubleshooting

### Backend won't start
- Check `AppData/Roaming/OCR Form Extractor/app.log`
- Verify `backend/api.exe` exists in resources
- Check port 8000 is available

### Frontend not loading
- Verify `frontend/index.html` exists in resources
- Check browser console (DevTools: Ctrl+Shift+I)
- Verify file paths are correct

### Build fails
- Ensure all dependencies are installed
- Check Python and Node.js versions
- Review build logs for specific errors

## Development Mode

Run in development:
```bash
cd electron
npm start
```

This will:
1. Start Python backend with uvicorn
2. Start Vite dev server
3. Open Electron window

## Production Build

For production distribution:
```bash
cd electron
npm run dist
```

This creates an installer that:
- Bundles backend executable
- Bundles frontend build
- Includes all dependencies
- Creates installer for target platform

## Distribution

After building, distribute:
- **Windows:** `electron/dist/OCR Form Extractor Setup X.X.X.exe`
- **Mac:** `electron/dist/OCR Form Extractor-X.X.X.dmg`
- **Linux:** `electron/dist/OCR Form Extractor-X.X.X.AppImage`
