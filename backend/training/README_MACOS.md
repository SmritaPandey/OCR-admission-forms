# OCR Model Training - macOS Guide

Complete guide for training OCR models on macOS.

## Prerequisites

### 1. Install Python 3.9+ (if not already installed)

```bash
# Check Python version
python3 --version

# If needed, install via Homebrew
brew install python@3.11
```

### 2. Install Homebrew (if not installed)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### 3. Install System Dependencies

```bash
# Install required system libraries
brew install libjpeg libpng libtiff
```

### 4. Install PyTorch and Training Dependencies

```bash
# Navigate to project directory
cd /Users/smrita/Documents/Projects/OCR-admission-forms

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate

# Install PyTorch (CPU version for macOS - MPS support for Apple Silicon)
# For Apple Silicon (M1/M2/M3):
pip install torch torchvision torchaudio

# For Intel Mac:
# pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Install training dependencies
pip install transformers datasets accelerate pillow

# Install other project dependencies
pip install -r requirements.txt
```

**Note:** Apple Silicon Macs (M1/M2/M3) can use Metal Performance Shaders (MPS) for GPU acceleration. PyTorch will automatically use MPS if available.

### 5. Verify Installation

```bash
# Test PyTorch
python3 -c "import torch; print(f'PyTorch: {torch.__version__}'); print(f'MPS available: {torch.backends.mps.is_available()}')"

# Test transformers
python3 -c "from transformers import TrOCRProcessor; print('Transformers OK')"
```

## Quick Start

### Step 1: Export Annotations

```bash
# From project root
curl http://127.0.0.1:8000/api/export/training-data?format=json > annotations.json
```

### Step 2: Prepare Training Data

```bash
# Navigate to training directory
cd backend/training

# Activate virtual environment if using one
source ../../venv/bin/activate

# Prepare data for both TrOCR and Donut
python3 prepare_data.py ../annotations.json \
  --format both \
  --split \
  --output-dir ../uploads/training_data
```

This will create:
- `../uploads/training_data/images/` - Extracted form images
- `../uploads/training_data/trocr_dataset.json` - TrOCR format
- `../uploads/training_data/donut_dataset.json` - Donut format
- `../uploads/training_data/train.json` - Training set
- `../uploads/training_data/val.json` - Validation set
- `../uploads/training_data/test.json` - Test set

### Step 3: Train TrOCR Model

```bash
# Train TrOCR (for handwritten text recognition)
python3 train_trocr.py \
  ../uploads/training_data/train.json \
  ../models/trocr_finetuned \
  --val-data ../uploads/training_data/val.json \
  --epochs 10 \
  --batch-size 4 \
  --learning-rate 5e-5 \
  --base-model microsoft/trocr-base-handwritten
```

**macOS Notes:**
- Use smaller batch sizes (4-8) due to memory constraints
- Training on CPU is slower but works fine
- Apple Silicon: MPS will be used automatically if available

### Step 4: Train Donut Model

```bash
# Train Donut (for structured form understanding)
python3 train_donut.py \
  ../uploads/training_data/train.json \
  ../models/donut_finetuned \
  --val-data ../uploads/training_data/val.json \
  --epochs 15 \
  --batch-size 2 \
  --learning-rate 3e-5
```

**macOS Notes:**
- Use very small batch sizes (2-4) for Donut due to high memory usage
- Consider using gradient accumulation instead

### Step 5: Evaluate Model

```bash
# Evaluate trained TrOCR model
python3 evaluate_model.py \
  ../models/trocr_finetuned \
  ../uploads/training_data/test.json \
  --output ../models/evaluation_report.json \
  --device cpu
```

## macOS-Specific Configuration

### Apple Silicon (M1/M2/M3) Optimization

If you have an Apple Silicon Mac, PyTorch can use Metal Performance Shaders:

```python
# In your training script, you can explicitly use MPS:
import torch
device = "mps" if torch.backends.mps.is_available() else "cpu"
```

The training scripts will automatically detect and use MPS if available.

### Memory Management

macOS has different memory constraints. Adjust batch sizes:

```bash
# For TrOCR on macOS
--batch-size 4  # Start with 4, increase if memory allows

# For Donut on macOS
--batch-size 2  # Donut needs more memory, use smaller batches
```

### Virtual Environment Best Practice

Always use a virtual environment:

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install transformers torch torchvision datasets accelerate

# Deactivate when done
deactivate
```

## Complete Training Workflow (macOS)

### 1. Setup Environment

```bash
# Navigate to project
cd /Users/smrita/Documents/Projects/OCR-admission-forms

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install torch torchvision torchaudio
pip install transformers datasets accelerate pillow
pip install -r requirements.txt
```

### 2. Collect Training Data

```bash
# Start backend server (in another terminal)
python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

# Export annotations
curl http://127.0.0.1:8000/api/export/training-data?format=json > annotations.json
```

### 3. Prepare Data

```bash
cd backend/training
python3 prepare_data.py ../../annotations.json --format both --split
```

### 4. Train Models

```bash
# Train TrOCR
python3 train_trocr.py \
  ../uploads/training_data/train.json \
  ../models/trocr_finetuned \
  --val-data ../uploads/training_data/val.json \
  --epochs 10 \
  --batch-size 4 \
  --base-model microsoft/trocr-base-handwritten

# Train Donut (optional, more memory intensive)
python3 train_donut.py \
  ../uploads/training_data/train.json \
  ../models/donut_finetuned \
  --val-data ../uploads/training_data/val.json \
  --epochs 15 \
  --batch-size 2
```

### 5. Evaluate

```bash
python3 evaluate_model.py \
  ../models/trocr_finetuned \
  ../uploads/training_data/test.json \
  --output ../models/eval_report.json
```

## macOS Troubleshooting

### Issue: "No module named 'torch'"

**Solution:**
```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Reinstall PyTorch
pip install torch torchvision torchaudio
```

### Issue: Out of Memory Errors

**Solution:**
- Reduce batch size: `--batch-size 2` or `--batch-size 1`
- Use gradient accumulation (already in Donut script)
- Close other applications
- Use CPU instead of MPS if MPS causes issues

### Issue: Slow Training

**Solution:**
- Use smaller models: `microsoft/trocr-small-printed` instead of `-base-`
- Reduce epochs for testing
- Use fewer training samples initially
- Consider cloud training (Google Colab, AWS) for faster results

### Issue: "libjpeg not found" or Image Loading Errors

**Solution:**
```bash
# Install system libraries
brew install libjpeg libpng libtiff

# Reinstall Pillow
pip install --upgrade --force-reinstall pillow
```

### Issue: MPS (Metal) Errors on Apple Silicon

**Solution:**
```bash
# Force CPU usage
export PYTORCH_ENABLE_MPS_FALLBACK=1

# Or in Python code, explicitly use CPU:
device = "cpu"
```

### Issue: "Permission denied" when saving models

**Solution:**
```bash
# Create models directory with proper permissions
mkdir -p backend/models
chmod 755 backend/models
```

## Performance Tips for macOS

1. **Use Apple Silicon MPS** (if available)
   - Automatically enabled in training scripts
   - Provides GPU-like acceleration

2. **Optimize Batch Sizes**
   - TrOCR: Start with 4, increase to 8 if memory allows
   - Donut: Use 2-4 maximum

3. **Monitor Memory Usage**
   ```bash
   # Check memory usage
   top -l 1 | grep "PhysMem"
   
   # Or use Activity Monitor
   open -a "Activity Monitor"
   ```

4. **Use Smaller Models for Testing**
   - `microsoft/trocr-small-printed` - Faster, less accurate
   - `microsoft/trocr-base-printed` - Balanced
   - `microsoft/trocr-base-handwritten` - Best for forms

5. **Train in Batches**
   - Train on subset first (50 samples)
   - Verify pipeline works
   - Then train on full dataset

## Example: Complete Training Session

```bash
# Terminal 1: Setup
cd /Users/smrita/Documents/Projects/OCR-admission-forms
python3 -m venv venv
source venv/bin/activate
pip install torch torchvision transformers datasets accelerate

# Terminal 2: Start backend (if needed)
cd /Users/smrita/Documents/Projects/OCR-admission-forms
source venv/bin/activate
python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

# Terminal 1: Training workflow
cd /Users/smrita/Documents/Projects/OCR-admission-forms
source venv/bin/activate

# Export data
curl http://127.0.0.1:8000/api/export/training-data?format=json > annotations.json

# Prepare
cd backend/training
python3 prepare_data.py ../../annotations.json --format trocr --split

# Train
python3 train_trocr.py \
  ../uploads/training_data/train.json \
  ../models/trocr_finetuned \
  --val-data ../uploads/training_data/val.json \
  --epochs 5 \
  --batch-size 4 \
  --base-model microsoft/trocr-base-handwritten

# Evaluate
python3 evaluate_model.py \
  ../models/trocr_finetuned \
  ../uploads/training_data/test.json
```

## System Requirements

**Minimum:**
- macOS 11.0+ (Big Sur)
- 8GB RAM
- 10GB free disk space
- Python 3.9+

**Recommended:**
- macOS 12.0+ (Monterey) or later
- 16GB+ RAM (for Donut training)
- Apple Silicon (M1/M2/M3) for MPS acceleration
- 20GB+ free disk space (for models and data)

## Next Steps

After training:
1. Test trained model on new forms
2. Compare accuracy with baseline
3. Fine-tune hyperparameters if needed
4. Deploy model for production use

See `README.md` for general training documentation and `TRAINING_AND_IMPROVEMENT_GUIDE.md` for detailed guides.

