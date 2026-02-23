# Quick Start: Building Desktop App

## Prerequisites Check

Run this first to check if you have everything:

```bash
scripts\check_requirements.bat
```

## Build Steps

### 1. Configure (Optional)

If you want to include your configuration in the installer:

```bash
# Create .env template
create_env_template.bat

# Edit .env with your settings
# Then bundle it
python scripts\bundle_config.py
```

### 2. Build

Simply run:

```bash
build_desktop.bat
```

This will:
- ✅ Install all dependencies
- ✅ Build Python backend → `backend-dist/api.exe`
- ✅ Build React frontend → `frontend/dist/`
- ✅ Package with Electron → `electron/dist/OCR Form Extractor Setup X.X.X.exe`

### 3. Install

Find your installer in:
```
electron\dist\OCR Form Extractor Setup X.X.X.exe
```

Double-click to install!

## What Gets Bundled?

✅ Python backend (as `api.exe`)  
✅ React frontend (optimized build)  
✅ All Python dependencies  
✅ Electron runtime  
✅ Configuration files (if bundled)  
✅ Database template (if exists)  

## Troubleshooting

**"Python not found"**
- Install Python 3.8+ from python.org
- Make sure "Add to PATH" is checked during installation

**"Node.js not found"**
- Install Node.js 18+ from nodejs.org
- Restart command prompt after installation

**Build fails at PyInstaller**
- Make sure all Python packages are installed: `pip install -r requirements.txt`
- Try: `pip install --upgrade pyinstaller`

**Build fails at frontend**
- Clear and reinstall: `cd frontend && rm -rf node_modules && npm install`

**Installer created but app won't start**
- Check Windows Event Viewer
- Check logs in `%APPDATA%/OCR Form Extractor/logs/`
- Make sure port 8000 is not in use

## Next Steps

After building:

1. **Test the installer** on a clean Windows machine
2. **Distribute** the `.exe` file to users
3. **Provide** `README_DESKTOP.md` to end users

## Need Help?

See `DESKTOP_APP_GUIDE.md` for detailed documentation.
