#!/bin/bash
# Setup script for CRAFT + TR-OCR
# Installs all dependencies and sets up the environment

set -e

echo "=========================================="
echo "CRAFT + TR-OCR Setup"
echo "=========================================="
echo ""

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

# Detect system
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "Detected: macOS"
    SYSTEM="macos"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "Detected: Linux"
    SYSTEM="linux"
else
    echo "Detected: Other (assuming Linux-like)"
    SYSTEM="linux"
fi

echo ""
echo "Step 1: Installing PyTorch..."
echo "----------------------------------------"

# Install PyTorch based on system
if [[ "$SYSTEM" == "macos" ]]; then
    # macOS - supports MPS (Apple Silicon)
    pip3 install torch torchvision torchaudio
elif command -v nvidia-smi &> /dev/null; then
    # Linux with NVIDIA GPU
    echo "NVIDIA GPU detected - installing CUDA version"
    pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
else
    # CPU only
    echo "No GPU detected - installing CPU version"
    pip3 install torch torchvision torchaudio
fi

echo ""
echo "Step 2: Installing CRAFT + TR-OCR dependencies..."
echo "----------------------------------------"

pip3 install transformers>=4.36.0
pip3 install accelerate
pip3 install craft-text-detector
pip3 install opencv-python
pip3 install pillow
pip3 install numpy
pip3 install tqdm

echo ""
echo "Step 3: Verifying installation..."
echo "----------------------------------------"

python3 -c "
import torch
print(f'✅ PyTorch: {torch.__version__}')
if torch.cuda.is_available():
    print(f'✅ CUDA available: {torch.cuda.get_device_name(0)}')
elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
    print('✅ Apple Silicon (MPS) available')
else:
    print('⚠️  Using CPU (no GPU detected)')

try:
    from transformers import TrOCRProcessor
    print('✅ Transformers installed')
except ImportError:
    print('❌ Transformers not installed')

try:
    import craft_text_detector
    print('✅ CRAFT installed')
except ImportError:
    print('❌ CRAFT not installed')
"

echo ""
echo "Step 4: Downloading pre-trained models..."
echo "----------------------------------------"
echo "This may take a few minutes on first run..."
echo ""

python3 -c "
from transformers import TrOCRProcessor, VisionEncoderDecoderModel
print('Downloading TR-OCR model...')
processor = TrOCRProcessor.from_pretrained('microsoft/trocr-base-handwritten')
model = VisionEncoderDecoderModel.from_pretrained('microsoft/trocr-base-handwritten')
print('✅ TR-OCR model downloaded')
"

echo ""
echo "=========================================="
echo "✅ Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Enable CRAFT+TR-OCR in your .env file:"
echo "   OCR_ENABLE_CRAFT_TROCR=true"
echo ""
echo "2. Test the installation:"
echo "   python test_craft_trocr.py --image your_image.jpg"
echo ""
echo "3. Read the guide:"
echo "   cat CRAFT_TROCR_GUIDE.md"
echo ""

