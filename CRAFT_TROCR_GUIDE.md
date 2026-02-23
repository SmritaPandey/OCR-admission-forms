# CRAFT + TR-OCR Complete Guide

## Overview

This guide teaches you how to use **CRAFT (Character Region Awareness for Text Detection)** and **TR-OCR (Transformer-Based OCR)** for extracting handwritten text from medical prescriptions and forms.

### What is CRAFT + TR-OCR?

- **CRAFT**: A deep learning algorithm that detects text regions in images by breaking down handwritten text into individual characters. It identifies where text is located in the image.

- **TR-OCR**: A transformer-based model that converts visual text into machine-readable characters. It uses an encoder-decoder architecture specifically trained for handwritten text recognition.

**Together**: CRAFT finds the text regions, and TR-OCR reads the handwritten text in each region.

## Table of Contents

1. [Installation](#installation)
2. [Quick Start](#quick-start)
3. [Understanding the Workflow](#understanding-the-workflow)
4. [Training Your Own Model](#training-your-own-model)
5. [Using the Trained Model](#using-the-trained-model)
6. [Data Management](#data-management)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

---

## Installation

### Step 1: Install Dependencies

```bash
# Install PyTorch (choose based on your system)
# For CUDA (NVIDIA GPU):
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# For CPU only:
pip install torch torchvision torchaudio

# For Apple Silicon (M1/M2/M3):
pip install torch torchvision torchaudio

# Install CRAFT and TR-OCR dependencies
pip install craft-text-detector transformers accelerate pillow opencv-python numpy

# Install additional utilities
pip install tqdm datasets
```

### Step 2: Download Pre-trained Models

The models will be automatically downloaded on first use:
- **CRAFT**: Text detection model (downloaded automatically)
- **TR-OCR**: `microsoft/trocr-base-handwritten` (downloaded automatically)

### Step 3: Enable in Configuration

Add to your `.env` file:

```env
OCR_ENABLE_CRAFT_TROCR=true
OCR_PROVIDER=craft-trocr
```

Or set via environment variable:

```bash
export OCR_ENABLE_CRAFT_TROCR=true
```

---

## Quick Start

### 1. Basic Usage (Using Pre-trained Model)

```python
from backend.ocr.ocr_factory import get_ocr_provider
from PIL import Image

# Load image
image = Image.open("prescription.jpg").convert("RGB")

# Get CRAFT+TR-OCR provider
provider = get_ocr_provider("craft-trocr")

# Extract text
result = await provider.extract_text(image)

print("Extracted text:", result["raw_text"])
print("Confidence:", result["confidence"])
print("Regions detected:", result["regions_detected"])
```

### 2. Using via API

```bash
# Upload and extract text
curl -X POST http://localhost:8000/api/upload \
  -F "file=@prescription.pdf" \
  -F "ocr_provider=craft-trocr"
```

### 3. Example: Extract Text from Medical Prescription

```python
import asyncio
from backend.ocr.craft_trocr_provider import CraftTrocrProvider
from PIL import Image

async def extract_prescription():
    # Initialize provider
    provider = CraftTrocrProvider()
    
    # Load prescription image
    image = Image.open("prescription.jpg").convert("RGB")
    
    # Extract text
    result = await provider.extract_text(image)
    
    # Print results
    print("=" * 60)
    print("Prescription Text Extraction")
    print("=" * 60)
    print(f"\nExtracted Text:\n{result['raw_text']}")
    print(f"\nConfidence: {result['confidence']:.2f}%")
    print(f"Regions Detected: {result['regions_detected']}")
    print(f"Regions Recognized: {result['regions_recognized']}")
    
    # Print each region
    print("\nRegion Details:")
    for i, region in enumerate(result.get('regions', []), 1):
        print(f"\nRegion {i}:")
        print(f"  Text: {region['text']}")
        print(f"  BBox: {region['bbox']}")
        print(f"  Confidence: {region['confidence']:.2f}%")

# Run
asyncio.run(extract_prescription())
```

---

## Understanding the Workflow

### How CRAFT + TR-OCR Works

```
Input Image
    ↓
[CRAFT Text Detection]
    ↓
Detected Text Regions (bounding boxes)
    ↓
[Crop Each Region]
    ↓
[TR-OCR Recognition] (for each region)
    ↓
Recognized Text
    ↓
[Combine All Text]
    ↓
Final Output
```

### Step-by-Step Process

1. **Text Detection (CRAFT)**:
   - CRAFT analyzes the image and identifies regions containing text
   - Returns bounding boxes/polygons for each text region
   - Works well for both printed and handwritten text

2. **Region Cropping**:
   - Each detected region is cropped from the original image
   - Regions are preprocessed (contrast enhancement, resizing)

3. **Text Recognition (TR-OCR)**:
   - Each cropped region is passed to TR-OCR
   - TR-OCR recognizes the handwritten text in the region
   - Uses transformer architecture for high accuracy

4. **Text Combination**:
   - All recognized text from all regions is combined
   - Maintains spatial information (bounding boxes)

---

## Training Your Own Model

### Why Train Your Own Model?

- **Domain-specific accuracy**: Better recognition for medical terminology, drug names, dosages
- **Handwriting style**: Adapts to specific handwriting styles in your data
- **Language support**: Can be fine-tuned for specific languages or scripts

### Step 1: Prepare Training Data

Your training data should be in JSON format:

```json
[
  {
    "image_path": "data/train/prescription_001.jpg",
    "text": "Dr. John Smith\nRx: Paracetamol 500mg\nTake 1 tablet twice daily"
  },
  {
    "image_path": "data/train/prescription_002.jpg",
    "text": "Patient: Jane Doe\nMedication: Amoxicillin 250mg\nDosage: 2 capsules every 8 hours"
  }
]
```

**Data Format Requirements:**
- Each entry has `image_path` and `text`
- `image_path` can be absolute or relative (use `--image-dir` for relative paths)
- `text` should be the exact text visible in the image
- Images should be cropped to show individual text regions (or full documents)

### Step 2: Split Data (Optional)

```python
import json
from sklearn.model_selection import train_test_split

# Load data
with open("all_data.json", "r") as f:
    data = json.load(f)

# Split 80% train, 20% validation
train_data, val_data = train_test_split(data, test_size=0.2, random_state=42)

# Save splits
with open("train.json", "w") as f:
    json.dump(train_data, f, indent=2)

with open("val.json", "w") as f:
    json.dump(val_data, f, indent=2)
```

### Step 3: Train the Model

#### Basic Training

```bash
cd backend/training

python train_craft_trocr.py \
  train.json \
  ../models/trocr_medical_prescriptions \
  --val-data val.json \
  --epochs 20 \
  --batch-size 8 \
  --learning-rate 5e-5 \
  --base-model microsoft/trocr-base-handwritten
```

#### Advanced Training (GPU with Mixed Precision)

```bash
python train_craft_trocr.py \
  train.json \
  ../models/trocr_medical_prescriptions \
  --val-data val.json \
  --epochs 30 \
  --batch-size 16 \
  --learning-rate 3e-5 \
  --base-model microsoft/trocr-base-handwritten \
  --fp16 \
  --gradient-accumulation 2 \
  --save-steps 250 \
  --eval-steps 250
```

#### Training on Apple Silicon (M1/M2/M3)

```bash
python train_craft_trocr.py \
  train.json \
  ../models/trocr_medical_prescriptions \
  --val-data val.json \
  --epochs 20 \
  --batch-size 4 \
  --learning-rate 5e-5 \
  --base-model microsoft/trocr-base-handwritten
```

### Step 4: Monitor Training

Training logs are saved to `checkpoints/logs/`. Monitor with:

```bash
# View logs
tensorboard --logdir backend/models/trocr_medical_prescriptions/checkpoints/logs
```

Or check the console output for:
- Training loss (should decrease)
- Validation loss (should decrease)
- Learning rate schedule

### Step 5: Training Parameters Explained

| Parameter | Description | Recommended Value |
|-----------|-------------|-------------------|
| `--epochs` | Number of training epochs | 20-30 for small datasets, 10-15 for large |
| `--batch-size` | Batch size | 8-16 (GPU), 4-8 (CPU/MPS) |
| `--learning-rate` | Learning rate | 5e-5 (default), 3e-5 (fine-tuning) |
| `--max-length` | Max sequence length | 128 (default), 256 (long text) |
| `--warmup-steps` | Warmup steps | 500 (default) |
| `--weight-decay` | Weight decay | 0.01 (default) |
| `--fp16` | Mixed precision | Use on GPU for 2x speedup |
| `--gradient-accumulation` | Gradient accumulation | 2-4 for larger effective batch size |

---

## Using the Trained Model

### Method 1: Environment Variable

```bash
export TROCR_CUSTOM_MODEL_PATH="/path/to/your/trained/model"
```

Then use the provider normally - it will automatically load your custom model.

### Method 2: Direct Path in Code

```python
from backend.ocr.craft_trocr_provider import CraftTrocrProvider

# Initialize with custom model
provider = CraftTrocrProvider(custom_model_path="/path/to/trained/model")

# Use normally
result = await provider.extract_text(image)
```

### Method 3: Update Provider Code

Edit `backend/ocr/craft_trocr_provider.py` and change the default model path.

---

## Data Management

### Organizing Training Data

```
training_data/
├── images/
│   ├── train/
│   │   ├── prescription_001.jpg
│   │   ├── prescription_002.jpg
│   │   └── ...
│   └── val/
│       ├── prescription_101.jpg
│       └── ...
├── train.json
└── val.json
```

### Data Collection Best Practices

1. **Quantity**: Aim for at least 100-200 samples for fine-tuning
2. **Quality**: Ensure text annotations are accurate
3. **Diversity**: Include various handwriting styles, image qualities, text lengths
4. **Domain-specific**: Include medical terms, drug names, dosages from your use case

### Data Annotation Tools

You can use:
- **Label Studio**: https://labelstud.io/
- **CVAT**: https://cvat.org/
- **Custom annotation interface**: Use the verification interface in this project

### Converting Existing Data

If you have data in other formats:

```python
import json
from pathlib import Path

# Convert from CSV
import pandas as pd
df = pd.read_csv("data.csv")
data = [
    {"image_path": row["image_path"], "text": row["text"]}
    for _, row in df.iterrows()
]
with open("train.json", "w") as f:
    json.dump(data, f, indent=2)
```

---

## Best Practices

### 1. Image Preprocessing

- **Resolution**: Use images with at least 300 DPI
- **Format**: PNG or JPEG (avoid compression artifacts)
- **Size**: Resize to reasonable dimensions (1280px max for CRAFT)

### 2. Training Tips

- **Start small**: Begin with 50-100 samples to test the pipeline
- **Monitor overfitting**: Watch validation loss - if it increases while training loss decreases, reduce learning rate or add more data
- **Use augmentation**: Enable data augmentation (`--no-augment` flag to disable)
- **Checkpointing**: Models are saved every `--save-steps` - you can resume training

### 3. Model Selection

- **Base model**: Use `microsoft/trocr-base-handwritten` for handwritten text
- **For printed text**: Use `microsoft/trocr-base-printed`
- **For both**: Fine-tune on mixed dataset

### 4. Performance Optimization

- **GPU**: Use GPU for 10-50x faster training
- **Batch size**: Increase batch size if you have GPU memory
- **Mixed precision**: Use `--fp16` on GPU for 2x speedup
- **Gradient accumulation**: Simulate larger batch sizes

### 5. Production Deployment

- **Model size**: Trained models are ~500MB - plan storage accordingly
- **Inference speed**: TR-OCR is fast on GPU, slower on CPU
- **Caching**: Cache model loading to avoid reloading on each request

---

## Troubleshooting

### Issue: "CRAFT is not installed"

**Solution:**
```bash
pip install craft-text-detector
```

### Issue: "CUDA out of memory"

**Solutions:**
1. Reduce batch size: `--batch-size 4`
2. Use gradient accumulation: `--gradient-accumulation 2`
3. Use CPU: Remove `--fp16` flag

### Issue: "Model download fails"

**Solution:**
```bash
# Download manually
from transformers import TrOCRProcessor, VisionEncoderDecoderModel
processor = TrOCRProcessor.from_pretrained("microsoft/trocr-base-handwritten")
model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-handwritten")
```

### Issue: "Training loss not decreasing"

**Solutions:**
1. Check learning rate (try 1e-5 or 3e-5)
2. Verify data format is correct
3. Check that images are loading properly
4. Try more training data

### Issue: "Poor recognition accuracy"

**Solutions:**
1. Train for more epochs
2. Use more training data
3. Ensure training data quality is high
4. Try different base model
5. Adjust image preprocessing

### Issue: "Slow inference on CPU"

**Solution:**
- Use GPU if available
- Consider using cloud OCR services for production
- Optimize image size before processing

---

## Example: Complete Training Workflow

```bash
# 1. Prepare data
python prepare_training_data.py --input-dir prescriptions/ --output train.json

# 2. Split data
python -c "
import json
from sklearn.model_selection import train_test_split
data = json.load(open('train.json'))
train, val = train_test_split(data, test_size=0.2, random_state=42)
json.dump(train, open('train_split.json', 'w'), indent=2)
json.dump(val, open('val_split.json', 'w'), indent=2)
"

# 3. Train model
python backend/training/train_craft_trocr.py \
  train_split.json \
  models/trocr_prescriptions \
  --val-data val_split.json \
  --epochs 20 \
  --batch-size 8 \
  --learning-rate 5e-5

# 4. Test model
export TROCR_CUSTOM_MODEL_PATH="models/trocr_prescriptions"
python test_craft_trocr.py --image test_prescription.jpg

# 5. Use in production
# Set environment variable or update provider code
```

---

## Resources

- **CRAFT Paper**: https://arxiv.org/abs/1904.01941
- **CRAFT GitHub**: https://github.com/clovaai/CRAFT-pytorch
- **TR-OCR Paper**: https://arxiv.org/abs/2109.10282
- **TR-OCR Hugging Face**: https://huggingface.co/microsoft/trocr-base-handwritten
- **Transformers Documentation**: https://huggingface.co/docs/transformers

---

## Support

For issues or questions:
1. Check this guide first
2. Review the training logs
3. Check GitHub issues
4. Contact the development team

---

**Happy Training! 🚀**

