# Quick Installation Guide

Fastest way to get everything installed and ready for training.

## 🚀 One-Command Installation

### macOS / Linux
```bash
chmod +x setup_complete.sh && ./setup_complete.sh
```

### Windows
```batch
setup_complete.bat
```

Or manually run:
```batch
install_training_dependencies.bat
```

---

## 📋 What Gets Installed

1. ✅ Python virtual environment
2. ✅ All Python dependencies (FastAPI, SQLAlchemy, etc.)
3. ✅ PyTorch (deep learning framework)
4. ✅ Transformers library (for TrOCR/Donut models)
5. ✅ Training utilities (datasets, accelerate, etc.)
6. ✅ OCR libraries (pytesseract, pdf2image, etc.)
7. ✅ Tesseract OCR (system-level)
8. ✅ Project directories (uploads, models, etc.)
9. ✅ .env configuration file

---

## ⚡ Step-by-Step (Manual)

### 1. Install Training Dependencies

**macOS / Linux:**
```bash
chmod +x install_training_dependencies.sh
./install_training_dependencies.sh
```

**Windows:**
```batch
install_training_dependencies.bat
```

### 2. Verify Installation

```bash
# Activate virtual environment
source venv/bin/activate  # macOS/Linux
# OR
venv\Scripts\activate  # Windows

# Test installations
python -c "import torch; print('PyTorch:', torch.__version__)"
python -c "import transformers; print('Transformers:', transformers.__version__)"
python -c "import fastapi; print('FastAPI:', fastapi.__version__)"
```

### 3. Start the Server

```bash
python -m uvicorn backend.main:app --reload --port 8000
```

### 4. Run Quick Training Setup

```bash
python backend/scripts/quick_train.py
```

---

## 🔍 Troubleshooting

### Python Not Found
- Install Python 3.8+ from https://www.python.org/downloads/
- Make sure Python is in your PATH

### Tesseract Not Found
**macOS:**
```bash
brew install tesseract
```

**Linux:**
```bash
sudo apt-get install tesseract-ocr  # Debian/Ubuntu
sudo yum install tesseract          # RedHat/CentOS
```

**Windows:**
- Download from: https://github.com/UB-Mannheim/tesseract/wiki
- Install to default location

### PyTorch Installation Issues
See detailed instructions in `INSTALL_ALL_DEPENDENCIES.md`

---

## 📚 More Information

- **Detailed Installation**: See `INSTALL_ALL_DEPENDENCIES.md`
- **Training Guide**: See `COMPLETE_TRAINING_GUIDE.md`
- **System Overview**: See `SYSTEM_OVERVIEW.md`

---

## ✅ Quick Checklist

After installation, verify:
- [ ] Virtual environment created and activated
- [ ] PyTorch installed (`python -c "import torch"`)
- [ ] Transformers installed (`python -c "import transformers"`)
- [ ] Tesseract installed (`tesseract --version`)
- [ ] Server starts (`python -m uvicorn backend.main:app`)
- [ ] Training script runs (`python backend/scripts/quick_train.py`)

---

## 🎯 Next Steps

1. **Configure .env file** with your settings
2. **Start the server**: `python -m uvicorn backend.main:app --reload`
3. **Upload forms**: Use the API or frontend
4. **Run training**: Follow `COMPLETE_TRAINING_GUIDE.md`

Ready to train! 🚀
