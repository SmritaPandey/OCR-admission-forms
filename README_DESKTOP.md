# OCR Admission Forms - Desktop App

A standalone Windows desktop application for digitizing student admission forms using OCR technology.

## Features

- ✅ **Fully Standalone**: No installation of Python, Node.js, or other dependencies required
- ✅ **All Features Included**: Complete OCR processing, form verification, student management
- ✅ **Offline Capable**: Works without internet (using local OCR providers)
- ✅ **Easy Installation**: Simple Windows installer (.exe)
- ✅ **Auto-Updates**: Optional auto-update support
- ✅ **Secure**: All secrets and credentials bundled securely

## Installation

### For End Users

1. Download the installer: `OCR Form Extractor Setup X.X.X.exe`
2. Run the installer
3. Follow the installation wizard
4. Launch the app from Start Menu or desktop shortcut

That's it! No additional setup required.

### First-Time Setup

On first launch, you may want to configure:

1. **OCR Provider**: Choose your preferred OCR provider
   - **Tesseract** (local, free, no internet required)
   - **CRAFT+TR-OCR** (local, best for handwriting, no internet required)
   - **Google Cloud Vision** (cloud, requires API key)
   - **Azure Form Recognizer** (cloud, requires credentials)
   - **AWS Textract** (cloud, requires credentials)

2. **API Keys** (if using cloud OCR):
   - Edit `%APPDATA%/OCR Form Extractor/data/.env`
   - Add your API keys
   - Restart the app

3. **Database**: The app creates a SQLite database automatically
   - Location: `%APPDATA%/OCR Form Extractor/data/admission_forms.db`
   - You can backup/restore this file

## Usage

### Upload Forms

1. Click "Upload Form" or drag & drop files
2. Select PDF or image files
3. Choose OCR provider (or use default)
4. Wait for processing

### Verify Forms

1. Open a form from the list
2. Review extracted data
3. Correct any errors
4. Click "Verify" to save

### Search & Export

1. Use the search interface to find forms
2. Filter by student name, enrollment number, etc.
3. Export to CSV, Excel, JSON, or PDF

### Batch Processing

1. Click "Batch Upload"
2. Select multiple files
3. Set pages per form (default: 3)
4. Monitor progress
5. Review results

## Configuration

### Environment Variables

Edit: `%APPDATA%/OCR Form Extractor/data/.env`

Key settings:

```env
# OCR Provider
OCR_PROVIDER=tesseract  # or craft-trocr, google-vision, etc.

# Google Cloud (if using)
GOOGLE_CLOUD_API_KEY=your_key_here
GOOGLE_CLOUD_PROJECT_ID=your_project_id

# Azure (if using)
AZURE_VISION_KEY=your_key_here
AZURE_VISION_ENDPOINT=your_endpoint_here

# Database
DATABASE_URL=sqlite:///./admission_forms.db
```

### Credentials Files

For Google Cloud Document AI, place your credentials file at:
`%APPDATA%/OCR Form Extractor/data/google-cloud-credentials.json`

## Troubleshooting

### App Won't Start

1. **Check Windows Event Viewer** for errors
2. **Check logs** at: `%APPDATA%/OCR Form Extractor/logs/`
3. **Restart your computer** (sometimes helps with port conflicts)
4. **Reinstall the app** if issues persist

### OCR Not Working

**Tesseract Issues:**
- Install Tesseract: https://github.com/UB-Mannheim/tesseract/wiki
- Add to PATH or configure in `.env`: `TESSERACT_CMD=C:/Program Files/Tesseract-OCR/tesseract.exe`

**Cloud OCR Issues:**
- Verify API keys in `.env` file
- Check internet connection
- Verify credentials file exists (for Google Cloud)
- Check API quotas/billing

### Database Issues

**Database locked:**
- Close the app completely
- Wait a few seconds
- Restart the app

**Database corrupted:**
- Backup: `%APPDATA%/OCR Form Extractor/data/admission_forms.db`
- Delete the database file
- Restart app (creates new database)
- Restore from backup if needed

### Performance Issues

**Slow OCR processing:**
- Use local providers (Tesseract, CRAFT+TR-OCR) for faster processing
- Reduce image size before uploading
- Close other applications

**App uses too much memory:**
- Process forms in smaller batches
- Close unused forms
- Restart the app periodically

## Data Location

All app data is stored in:

```
%APPDATA%/OCR Form Extractor/
├── data/
│   ├── .env                    # Configuration
│   ├── admission_forms.db     # Database
│   ├── google-cloud-credentials.json  # Google credentials (if used)
│   └── uploads/                # Uploaded files
└── logs/                       # Application logs
```

**Backup**: Copy the entire `data/` folder to backup your work.

## Uninstallation

1. Go to Windows Settings → Apps
2. Find "OCR Form Extractor"
3. Click "Uninstall"

**Note**: Uninstallation does NOT delete your data. To completely remove:
- Uninstall the app
- Delete: `%APPDATA%/OCR Form Extractor/`

## System Requirements

- **OS**: Windows 10 or later
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 500MB for app + space for your data
- **Internet**: Optional (only needed for cloud OCR providers)

## Support

For help:

1. Check this README
2. Check `DESKTOP_APP_GUIDE.md` for developers
3. Check main `README.md` for general documentation
4. Open an issue on GitHub

## License

[Your License Here]

---

**Built with ❤️ using Electron, FastAPI, and React**
