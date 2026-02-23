# Desktop App Build Guide

This guide explains how to build and distribute the OCR Admission Forms desktop application for Windows.

## Prerequisites

Before building the desktop app, ensure you have:

1. **Python 3.8+** installed and in PATH
   - Download from [python.org](https://www.python.org/downloads/)
   - Make sure to check "Add Python to PATH" during installation

2. **Node.js 18+** installed and in PATH
   - Download from [nodejs.org](https://nodejs.org/)
   - This includes npm

3. **Tesseract OCR** (optional, for local OCR)
   - Download from [GitHub](https://github.com/UB-Mannheim/tesseract/wiki)
   - Add to PATH or configure in `.env`

4. **API Keys** (optional, for cloud OCR providers)
   - Google Cloud Vision API key
   - Azure credentials
   - AWS credentials
   - Or use local Tesseract/CRAFT+TR-OCR

## Quick Start

### 1. Configure Environment

First, create your `.env` file with your configuration:

```bash
# Windows
create_env_template.bat

# Or manually create .env file
```

Edit `.env` and add your API keys and configuration. For a fully offline/local setup:

```env
OCR_PROVIDER=tesseract
OCR_ENABLE_TESSERACT=true
OCR_ENABLE_CRAFT_TROCR=true
# ... other settings
```

### 2. Bundle Configuration

Bundle your configuration files (optional, for including in the installer):

```bash
python scripts/bundle_config.py
```

This copies `.env`, `google-cloud-credentials.json`, and `admission_forms.db` to the `data/` directory.

### 3. Build Desktop App

Run the build script:

```bash
# Windows
build_desktop.bat

# Linux/Mac (for cross-platform builds)
./build_desktop.sh
```

The build process will:

1. Install Python dependencies
2. Install PyInstaller
3. Build Python backend as `api.exe`
4. Install frontend dependencies
5. Build frontend with Vite
6. Install Electron dependencies
7. Package everything into a Windows installer

### 4. Find Your Installer

After building, the installer will be in:

```
electron/dist/OCR Form Extractor Setup X.X.X.exe
```

## Build Process Details

### Backend Packaging (PyInstaller)

The Python backend is packaged using PyInstaller with the spec file `build_backend.spec`. This creates a standalone executable that includes:

- All Python dependencies
- Backend code
- Required data files

The executable is created as `backend-dist/api.exe`.

### Frontend Packaging (Vite)

The React frontend is built using Vite:

```bash
cd frontend
npm install
npm run build
```

This creates optimized production files in `frontend/dist/`.

### Electron Packaging (electron-builder)

Electron bundles everything together:

- Electron runtime
- Backend executable (`api.exe`)
- Frontend build files
- Configuration files
- Database (if included)

The final installer is created using NSIS (Windows installer).

## Configuration Files

### Environment Variables

The desktop app looks for configuration in this order:

1. `data/.env` (bundled with app)
2. User's home directory `.env` (optional)
3. Default values from `backend/config.py`

### Credentials

If using cloud OCR providers, include credentials:

- **Google Cloud**: `google-cloud-credentials.json` → `data/google-cloud-credentials.json`
- **Azure**: Configure in `.env` file
- **AWS**: Configure in `.env` file

### Database

The SQLite database is stored in:
- Development: `admission_forms.db` (project root)
- Desktop app: `data/admission_forms.db` (in app resources)

## Distribution

### Creating a Distribution Package

1. **Build the installer** (see Quick Start)
2. **Test the installer** on a clean Windows machine
3. **Create a release package**:
   - Installer: `electron/dist/OCR Form Extractor Setup X.X.X.exe`
   - README: Instructions for users
   - Optional: Sample forms for testing

### User Installation

Users simply need to:

1. Download the installer
2. Run `OCR Form Extractor Setup X.X.X.exe`
3. Follow the installation wizard
4. Launch the app from Start Menu or desktop shortcut

No additional setup required! All dependencies are bundled.

## Troubleshooting

### Build Fails

**Python not found:**
- Ensure Python is in PATH
- Try `python --version` in command prompt

**Node.js not found:**
- Ensure Node.js is in PATH
- Try `node --version` in command prompt

**PyInstaller fails:**
- Check Python version (3.8+ required)
- Ensure all dependencies are installed: `pip install -r requirements.txt`

**Frontend build fails:**
- Clear node_modules: `cd frontend && rm -rf node_modules && npm install`
- Check Node.js version (18+ required)

### App Won't Start

**Backend won't start:**
- Check Windows Event Viewer for errors
- Check `%APPDATA%/ocr-form-extractor/logs/` for log files
- Ensure port 8000 is not in use

**Frontend won't load:**
- Check that backend is running (should start automatically)
- Check browser console (F12) for errors
- Verify `frontend/dist/` exists in app resources

### OCR Not Working

**Tesseract not found:**
- Install Tesseract and add to PATH
- Or configure path in `.env`: `TESSERACT_CMD=C:/Program Files/Tesseract-OCR/tesseract.exe`

**Cloud OCR not working:**
- Verify API keys in `.env` or `data/.env`
- Check internet connection
- Verify credentials file exists (for Google Cloud)

## Advanced Configuration

### Custom Icon

Replace `electron/resources/icon.ico` with your icon file.

### Custom Installer

Edit `electron/package.json` → `build` section to customize:

- App name
- Installer options
- File associations
- Auto-updater settings

### Including Additional Files

Add files to `electron/package.json` → `build.extraResources`:

```json
{
  "from": "../path/to/file",
  "to": "destination/path"
}
```

## Development Mode

To run the app in development mode:

```bash
# Terminal 1: Start backend
python -m uvicorn backend.main:app --reload

# Terminal 2: Start frontend
cd frontend
npm run dev

# Terminal 3: Start Electron
cd electron
npm start
```

## Security Notes

⚠️ **Important**: When distributing the app:

1. **API Keys**: Don't include real API keys in the installer
   - Use placeholder values
   - Let users configure their own keys
   - Or use environment variables

2. **Credentials Files**: Don't include real credential files
   - Users should add their own
   - Or provide a setup wizard

3. **Database**: Consider starting with an empty database
   - Users can import data later
   - Or provide sample data separately

## Support

For issues or questions:

1. Check this guide
2. Check main README.md
3. Open an issue on GitHub

## License

[Your License Here]
