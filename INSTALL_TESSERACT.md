# Installing Tesseract OCR on macOS

## Quick Installation (Requires Admin Access)

### Option 1: Using Homebrew (Recommended)

**Step 1: Install Homebrew** (if not installed)
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

**Step 2: Install Tesseract**
```bash
brew install tesseract
```

**Step 3: Verify Installation**
```bash
tesseract --version
```

### Option 2: Using MacPorts

If you have MacPorts installed:
```bash
sudo port install tesseract
```

### Option 3: Manual Installation

1. Download Tesseract from: https://github.com/tesseract-ocr/tesseract/releases
2. Or use the installer: https://github.com/tesseract-ocr/tesseract/wiki/Installation#macos

### Option 4: Using Conda (if you have Anaconda/Miniconda)

```bash
conda install -c conda-forge tesseract
```

## After Installation

1. **Restart the backend server:**
   ```bash
   # Stop current server (Ctrl+C)
   # Then restart:
   cd /Users/smrita/Documents/Projects/OCR-admission-forms
   python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
   ```

2. **Verify Tesseract is available:**
   ```bash
   curl http://127.0.0.1:8000/api/providers
   ```
   Should show `"tesseract"` in the providers list.

3. **Test with empty form:**
   - Navigate to http://localhost:5173/upload
   - Upload `data/samples/pdfs/student data form scanned.pdf`
   - Select "Tesseract (Default)" as OCR provider
   - Upload and view results

## Alternative: Use AI OCR Providers

If you can't install Tesseract, you can use AI providers instead:

### GPT-4 Vision
1. Get API key from: https://platform.openai.com/api-keys
2. Add to `.env` file:
   ```
   OPENAI_API_KEY=your_key_here
   ```

### Claude Vision
1. Get API key from: https://console.anthropic.com/
2. Add to `.env` file:
   ```
   ANTHROPIC_API_KEY=your_key_here
   ```

### Ollama (Local AI - No API key needed)
1. Install Ollama: https://ollama.ai/download
2. Run: `ollama pull llama3.2-vision`
3. Start Ollama server (usually runs automatically)
4. Use "Ollama (Local AI)" provider in the UI

## Current Status

✅ **Python Dependencies:** All installed
- fastapi, uvicorn, sqlalchemy, pillow, pytesseract

❌ **Tesseract Binary:** Not installed
- Requires manual installation (see above)

✅ **Backend & Frontend:** Running
- Backend: http://127.0.0.1:8000
- Frontend: http://localhost:5173

## Next Steps

1. Install Tesseract using one of the methods above
2. Restart backend server
3. Test empty form upload
4. Or configure AI providers as alternative


