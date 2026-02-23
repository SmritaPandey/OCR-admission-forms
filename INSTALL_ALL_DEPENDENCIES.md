# Complete Dependency Installation Guide

This guide helps you install all dependencies needed for the OCR training system.

## 🚀 Quick Installation

### macOS / Linux
```bash
chmod +x install_training_dependencies.sh
./install_training_dependencies.sh
```

### Windows
```batch
install_training_dependencies.bat
```

---

## 📦 What Gets Installed

### 1. System Dependencies

#### macOS
- Homebrew (if not installed)
- libjpeg, libpng, libtiff (via Homebrew)

#### Linux (Debian/Ubuntu)
```bash
sudo apt-get update
sudo apt-get install -y \
    python3-dev \
    python3-pip \
    libjpeg-dev \
    zlib1g-dev \
    libtiff-dev \
    libpng-dev \
    build-essential \
    cmake
```

#### Linux (RedHat/CentOS/Fedora)
```bash
sudo yum install -y \
    python3-devel \
    python3-pip \
    libjpeg-devel \
    zlib-devel \
    libtiff-devel \
    libpng-devel \
    gcc \
    gcc-c++ \
    cmake
```

### 2. Python Dependencies

#### Core Training Libraries
- **PyTorch** - Deep learning framework
- **Transformers** - Hugging Face transformers (for TrOCR, Donut)
- **Datasets** - Dataset handling
- **Accelerate** - Training acceleration

#### Image Processing
- **Pillow** - Image manipulation
- **OpenCV** - Computer vision
- **NumPy** - Numerical computing

#### Training Utilities
- **scikit-learn** - Machine learning utilities
- **tqdm** - Progress bars
- **TensorBoard** - Training visualization

#### OCR Libraries
- **pytesseract** - Tesseract OCR wrapper
- **pdf2image** - PDF to image conversion
- **PyMuPDF** - PDF processing

#### API Dependencies
- **FastAPI** - Web framework
- **Uvicorn** - ASGI server
- **SQLAlchemy** - Database ORM
- **Pydantic** - Data validation

### 3. Optional Cloud OCR Dependencies

Install these only if using cloud OCR providers:

```bash
# Google Cloud Vision
pip install google-cloud-vision>=3.7.0

# Google Document AI
pip install google-cloud-documentai>=2.20.0

# Azure Form Recognizer
pip install azure-ai-formrecognizer>=3.3.0

# AWS Textract
pip install boto3>=1.34.0
```

---

## 🔧 Manual Installation

If you prefer to install manually:

### Step 1: Create Virtual Environment

```bash
# macOS/Linux
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### Step 2: Install Base Dependencies

```bash
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

### Step 3: Install PyTorch

**macOS (Apple Silicon M1/M2/M3):**
```bash
pip install torch torchvision torchaudio
```

**macOS (Intel) / Linux / Windows (CPU):**
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
```

**Linux / Windows (CUDA GPU):**
```bash
# CUDA 11.8
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# CUDA 12.1
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### Step 4: Install Training Dependencies

```bash
pip install -r requirements-training.txt
```

Or install individually:
```bash
pip install transformers>=4.36.0 datasets>=2.16.0 accelerate>=0.25.0
pip install scikit-learn>=1.3.0 tqdm>=4.65.0 tensorboard>=2.14.0
```

---

## ✅ Verify Installation

After installation, verify everything works:

```bash
# Activate virtual environment
source venv/bin/activate  # macOS/Linux
# OR
venv\Scripts\activate  # Windows

# Check PyTorch
python -c "import torch; print(f'PyTorch {torch.__version__}')"

# Check Transformers
python -c "import transformers; print(f'Transformers {transformers.__version__}')"

# Check Datasets
python -c "import datasets; print(f'Datasets {datasets.__version__}')"

# Check FastAPI
python -c "import fastapi; print(f'FastAPI {fastapi.__version__}')"
```

---

## 📋 System Requirements

### Minimum Requirements
- **Python**: 3.8 or higher
- **RAM**: 8GB (16GB recommended for training)
- **Storage**: 10GB free space
- **OS**: macOS, Linux, or Windows

### Recommended for Training
- **RAM**: 16GB or more
- **CPU**: Multi-core processor (4+ cores)
- **GPU**: CUDA-compatible GPU (optional but recommended for faster training)
- **Storage**: 20GB+ free space (for models and datasets)

### macOS Specific
- **Apple Silicon** (M1/M2/M3): PyTorch with MPS support
- **Intel Mac**: Standard PyTorch

---

## 🐛 Troubleshooting

### PyTorch Installation Issues

**Problem**: PyTorch fails to install
**Solutions**:
1. Upgrade pip: `pip install --upgrade pip`
2. Install from specific index (see Step 3 above)
3. Check Python version: `python --version` (need 3.8+)

### Transformers Installation Issues

**Problem**: Transformers fails to install
**Solutions**:
1. Ensure PyTorch is installed first
2. Upgrade pip: `pip install --upgrade pip`
3. Install in order: `pip install transformers datasets accelerate`

### Tesseract Not Found

**Problem**: `pytesseract` works but Tesseract not found
**Solutions**:

**macOS:**
```bash
brew install tesseract
```

**Linux (Debian/Ubuntu):**
```bash
sudo apt-get install tesseract-ocr
```

**Windows:**
1. Download from: https://github.com/UB-Mannheim/tesseract/wiki
2. Install to default location
3. Add to PATH or set environment variable:
   ```batch
   set TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
   ```

### PDF2Image Issues

**Problem**: pdf2image fails to convert PDFs
**Solutions**:

**macOS:**
```bash
brew install poppler
```

**Linux (Debian/Ubuntu):**
```bash
sudo apt-get install poppler-utils
```

**Windows:**
1. Download poppler from: https://github.com/oschwartz10612/poppler-windows/releases
2. Extract and add `bin` folder to PATH

### Out of Memory During Training

**Problem**: Training runs out of memory
**Solutions**:
1. Reduce batch size: `--batch-size 4` (or 2)
2. Use gradient accumulation
3. Train on smaller subset first
4. Close other applications
5. Use CPU instead of GPU (slower but less memory)

### Import Errors

**Problem**: Module not found errors
**Solutions**:
1. Ensure virtual environment is activated
2. Reinstall: `pip install -r requirements.txt -r requirements-training.txt`
3. Check Python path: `python -c "import sys; print(sys.path)"`

---

## 🔄 Update Dependencies

To update all dependencies:

```bash
# Activate virtual environment
source venv/bin/activate  # macOS/Linux
# OR
venv\Scripts\activate  # Windows

# Upgrade pip
pip install --upgrade pip

# Upgrade all packages
pip install --upgrade -r requirements.txt -r requirements-training.txt

# Or upgrade specific packages
pip install --upgrade transformers datasets accelerate
```

---

## 📚 Additional Resources

- **PyTorch Installation**: https://pytorch.org/get-started/locally/
- **Transformers Documentation**: https://huggingface.co/docs/transformers
- **Tesseract OCR**: https://github.com/tesseract-ocr/tesseract
- **Training Guide**: See `COMPLETE_TRAINING_GUIDE.md`

---

## ✅ Installation Checklist

- [ ] Python 3.8+ installed
- [ ] Virtual environment created and activated
- [ ] Base dependencies installed (`requirements.txt`)
- [ ] PyTorch installed (correct version for your system)
- [ ] Training dependencies installed (`requirements-training.txt`)
- [ ] Tesseract OCR installed (for local OCR)
- [ ] Poppler installed (for PDF processing)
- [ ] All packages verified with import tests
- [ ] `.env` file configured
- [ ] Training script tested

---

## 🎯 Next Steps

After installation:

1. **Configure environment**: Set up `.env` file
2. **Start the server**: `python -m uvicorn backend.main:app --reload`
3. **Run quick training**: `python backend/scripts/quick_train.py`
4. **Follow training guide**: See `COMPLETE_TRAINING_GUIDE.md`

---

## 💡 Tips

1. **Use virtual environment**: Always work within the virtual environment
2. **Install PyTorch first**: Some packages depend on PyTorch
3. **Check versions**: Ensure compatible versions of all packages
4. **GPU support**: If you have NVIDIA GPU, install CUDA version of PyTorch
5. **Apple Silicon**: M1/M2/M3 Macs get automatic MPS acceleration

For issues, check the troubleshooting section or see the main documentation.
