# CRAFT + TR-OCR Quick Start

## 🚀 5-Minute Setup

### 1. Install Dependencies

**macOS / Linux:**
```bash
./setup_craft_trocr.sh
```

**Or manually:**
```bash
# Install PyTorch
pip install torch torchvision torchaudio

# Install CRAFT + TR-OCR
pip install transformers craft-text-detector opencv-python pillow numpy
```

### 2. Enable in Configuration

Add to `.env`:
```env
OCR_ENABLE_CRAFT_TROCR=true
```

### 3. Test It!

```bash
# Test on an image
python test_craft_trocr.py --image prescription.jpg

# Or use via API
curl -X POST http://localhost:8000/api/upload \
  -F "file=@prescription.pdf" \
  -F "ocr_provider=craft-trocr"
```

## 📚 Training Your Model

### Step 1: Prepare Data

Create `train.json`:
```json
[
  {
    "image_path": "data/prescription_001.jpg",
    "text": "Dr. John Smith\nRx: Paracetamol 500mg"
  }
]
```

### Step 2: Train

```bash
python backend/training/train_craft_trocr.py \
  train.json \
  models/my_trained_model \
  --epochs 20 \
  --batch-size 8 \
  --learning-rate 5e-5
```

### Step 3: Use Trained Model

```bash
export TROCR_CUSTOM_MODEL_PATH="models/my_trained_model"
python test_craft_trocr.py --image test.jpg --model models/my_trained_model
```

## 📖 Full Documentation

See [CRAFT_TROCR_GUIDE.md](CRAFT_TROCR_GUIDE.md) for complete documentation.

## 💡 Key Features

- ✅ **CRAFT**: Detects text regions in images
- ✅ **TR-OCR**: Recognizes handwritten text
- ✅ **Training**: Fine-tune on your data
- ✅ **GPU Support**: Fast training on NVIDIA GPUs
- ✅ **Apple Silicon**: Works on M1/M2/M3 Macs
- ✅ **Data Management**: Tools for data preparation

## 🎯 Use Cases

- Medical prescriptions
- Handwritten forms
- Notes and documents
- Any handwritten text extraction

---

**Ready to extract handwritten text! 🎉**

