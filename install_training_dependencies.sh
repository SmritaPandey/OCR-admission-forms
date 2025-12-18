#!/bin/bash

# Installation script for OCR Training Dependencies
# This script installs all dependencies needed for training OCR models

set -e  # Exit on error

echo "=========================================="
echo "OCR Training Dependencies Installation"
echo "=========================================="
echo ""

# Detect OS
OS="$(uname -s)"
case "${OS}" in
    Linux*)     MACHINE=Linux;;
    Darwin*)    MACHINE=Mac;;
    CYGWIN*)    MACHINE=Cygwin;;
    MINGW*)     MACHINE=MinGW;;
    *)          MACHINE="UNKNOWN:${OS}"
esac

echo "Detected OS: $MACHINE"
echo ""

# Check Python version
echo "Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $PYTHON_VERSION"

# Check if Python 3.8+
if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"; then
    echo "❌ Python 3.8+ is required. Please install Python 3.8 or higher."
    exit 1
fi

echo "✅ Python version OK"
echo ""

# Install system dependencies
echo "=========================================="
echo "Installing System Dependencies"
echo "=========================================="

if [ "$MACHINE" = "Mac" ]; then
    echo "Installing macOS dependencies..."
    
    # Check if Homebrew is installed
    if ! command -v brew &> /dev/null; then
        echo "Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    fi
    
    # Install system libraries
    brew install libjpeg libpng libtiff || echo "Some packages may already be installed"
    
elif [ "$MACHINE" = "Linux" ]; then
    echo "Installing Linux dependencies..."
    
    # Detect Linux distribution
    if [ -f /etc/debian_version ]; then
        # Debian/Ubuntu
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
    elif [ -f /etc/redhat-release ]; then
        # RedHat/CentOS/Fedora
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
    fi
fi

echo "✅ System dependencies installed"
echo ""

# Create virtual environment if it doesn't exist
echo "=========================================="
echo "Setting up Python Virtual Environment"
echo "=========================================="

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

echo "✅ Virtual environment activated"
echo ""

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip setuptools wheel

echo "✅ pip upgraded"
echo ""

# Install PyTorch first (important for compatibility)
echo "=========================================="
echo "Installing PyTorch"
echo "=========================================="

if [ "$MACHINE" = "Mac" ]; then
    # macOS - check if Apple Silicon
    if [[ $(uname -m) == 'arm64' ]]; then
        echo "Detected Apple Silicon (M1/M2/M3). Installing PyTorch with MPS support..."
        pip install torch torchvision torchaudio
    else
        echo "Detected Intel Mac. Installing PyTorch..."
        pip install torch torchvision torchaudio
    fi
else
    # Linux/Windows - install CPU version by default (change if you have GPU)
    echo "Installing PyTorch (CPU version)..."
    echo "Note: If you have CUDA GPU, install PyTorch with CUDA support from pytorch.org"
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
fi

echo "✅ PyTorch installed"
echo ""

# Install training dependencies
echo "=========================================="
echo "Installing Training Dependencies"
echo "=========================================="

pip install \
    transformers>=4.36.0 \
    datasets>=2.16.0 \
    accelerate>=0.25.0 \
    pillow>=10.0.0 \
    numpy>=1.24.0 \
    scikit-learn>=1.3.0 \
    tqdm>=4.65.0 \
    tensorboard>=2.14.0

echo "✅ Training dependencies installed"
echo ""

# Install OCR and image processing dependencies
echo "=========================================="
echo "Installing OCR Dependencies"
echo "=========================================="

pip install \
    pytesseract>=0.3.10 \
    pdf2image>=1.16.3 \
    PyMuPDF>=1.23.0 \
    opencv-python>=4.8.0 \
    numpy>=1.24.0

echo "✅ OCR dependencies installed"
echo ""

# Install API dependencies (if not already installed)
echo "=========================================="
echo "Installing API Dependencies"
echo "=========================================="

pip install \
    fastapi>=0.100.0 \
    uvicorn[standard]>=0.23.0 \
    python-multipart>=0.0.6 \
    pydantic>=2.0.0 \
    pydantic-settings>=2.0.0 \
    sqlalchemy>=2.0.0 \
    requests>=2.31.0

echo "✅ API dependencies installed"
echo ""

# Install optional cloud OCR dependencies (user can enable if needed)
echo "=========================================="
echo "Optional Cloud OCR Dependencies"
echo "=========================================="
echo ""
echo "The following are optional and only needed if using cloud OCR providers:"
echo ""
echo "Google Cloud Vision:"
echo "  pip install google-cloud-vision>=3.7.0"
echo ""
echo "Google Document AI:"
echo "  pip install google-cloud-documentai>=2.20.0"
echo ""
echo "Azure Form Recognizer:"
echo "  pip install azure-ai-formrecognizer>=3.3.0"
echo ""
echo "AWS Textract:"
echo "  pip install boto3>=1.34.0"
echo ""
echo "Would you like to install any of these now? (y/n)"
read -r response
if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    echo ""
    echo "Installing all cloud OCR dependencies..."
    pip install \
        google-cloud-vision>=3.7.0 \
        google-cloud-documentai>=2.20.0 \
        azure-ai-formrecognizer>=3.3.0 \
        azure-cognitiveservices-vision-computervision>=0.9.0 \
        boto3>=1.34.0
    echo "✅ Cloud OCR dependencies installed"
else
    echo "Skipping cloud OCR dependencies. Install manually if needed."
fi

echo ""

# Verify installations
echo "=========================================="
echo "Verifying Installations"
echo "=========================================="

python3 -c "import torch; print(f'✅ PyTorch {torch.__version__}')" || echo "❌ PyTorch not installed correctly"
python3 -c "import transformers; print(f'✅ Transformers {transformers.__version__}')" || echo "❌ Transformers not installed"
python3 -c "import datasets; print(f'✅ Datasets {datasets.__version__}')" || echo "❌ Datasets not installed"
python3 -c "import PIL; print(f'✅ Pillow {PIL.__version__}')" || echo "❌ Pillow not installed"
python3 -c "import fastapi; print(f'✅ FastAPI {fastapi.__version__}')" || echo "❌ FastAPI not installed"

echo ""
echo "=========================================="
echo "Installation Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Activate the virtual environment: source venv/bin/activate"
echo "2. Install Tesseract OCR if not already installed"
echo "3. Set up your .env file with configuration"
echo "4. Run the training script: python backend/scripts/quick_train.py"
echo ""
echo "For detailed instructions, see COMPLETE_TRAINING_GUIDE.md"
