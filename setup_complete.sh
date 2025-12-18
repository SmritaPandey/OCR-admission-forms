#!/bin/bash

# Complete setup script - Installs everything needed
# This is a convenience script that runs all setup steps

set -e

echo "=========================================="
echo "Complete OCR Training System Setup"
echo "=========================================="
echo ""

# Step 1: Install training dependencies
echo "Step 1/4: Installing training dependencies..."
if [ -f "install_training_dependencies.sh" ]; then
    chmod +x install_training_dependencies.sh
    ./install_training_dependencies.sh
else
    echo "install_training_dependencies.sh not found, running manual installation..."
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt -r requirements-training.txt
fi

echo ""
echo "Step 2/4: Installing Tesseract OCR..."
echo ""

# Check if Tesseract is installed
if command -v tesseract &> /dev/null; then
    echo "✅ Tesseract is already installed: $(tesseract --version | head -n 1)"
else
    echo "Tesseract not found. Installing..."
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            brew install tesseract
        else
            echo "Please install Homebrew first, then run: brew install tesseract"
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        if [ -f /etc/debian_version ]; then
            sudo apt-get update
            sudo apt-get install -y tesseract-ocr
        elif [ -f /etc/redhat-release ]; then
            sudo yum install -y tesseract
        else
            echo "Please install Tesseract manually for your Linux distribution"
        fi
    else
        echo "Please install Tesseract manually. See INSTALL_ALL_DEPENDENCIES.md"
    fi
fi

echo ""
echo "Step 3/4: Creating necessary directories..."
mkdir -p uploads/training_data
mkdir -p uploads/training_data/images
mkdir -p models
mkdir -p logs

echo "✅ Directories created"
echo ""

echo "Step 4/4: Setting up .env file..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "✅ Created .env file from .env.example"
        echo "   Please edit .env file with your configuration"
    else
        echo "⚠️  .env.example not found. Creating basic .env file..."
        cat > .env << EOF
# Database
DATABASE_URL=sqlite:///./admission_forms.db

# OCR Provider
OCR_PROVIDER=tesseract-google-combined
OCR_ENABLE_TESSERACT=true
OCR_ENABLE_GOOGLE_VISION=true
OCR_ENABLE_TESSERACT_GOOGLE_COMBINED=true

# File Upload
UPLOAD_DIR=uploads
MAX_FILE_SIZE=10485760

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
EOF
        echo "✅ Created basic .env file"
    fi
else
    echo "✅ .env file already exists"
fi

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Activate virtual environment: source venv/bin/activate"
echo "2. Edit .env file with your configuration (if needed)"
echo "3. Start the server: python -m uvicorn backend.main:app --reload"
echo "4. Run training: python backend/scripts/quick_train.py"
echo ""
echo "For detailed instructions, see:"
echo "  - INSTALL_ALL_DEPENDENCIES.md"
echo "  - COMPLETE_TRAINING_GUIDE.md"
echo ""
