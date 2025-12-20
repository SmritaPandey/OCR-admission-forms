# 🚀 Training All OCR Providers - Complete Guide

## 📋 Training Workflow

### Step 1: Prepare Training Data from Images

We have **185 images** from converted PDFs ready for training.

```bash
# Prepare training data using Tesseract (most reliable)
python3 backend/scripts/prepare_training_from_images_simple.py
```

This will:
- Process all 185 images
- Extract text using Tesseract
- Save to `training_data/student_forms.json`

### Step 2: Train CRAFT+TR-OCR (Best Pipeline)

```bash
# Train CRAFT+TR-OCR on the prepared data
python3 backend/training/train_craft_trocr.py \
  training_data/student_forms.json \
  models/trocr_student_forms \
  --epochs 20 \
  --batch-size 8 \
  --image-dir . \
  --base-model microsoft/trocr-base-handwritten
```

### Step 3: Use Trained Model

Add to `.env`:
```env
TROCR_CUSTOM_MODEL_PATH=models/trocr_student_forms
```

Restart backend - CRAFT+TR-OCR will use your trained model!

---

## 🎯 Training All Providers

### 1. CRAFT+TR-OCR (Best for Handwritten) ⭐
```bash
python3 backend/training/train_craft_trocr.py \
  training_data/student_forms.json \
  models/trocr_student_forms \
  --epochs 20
```

### 2. CRAFT Only (Text Detection)
- CRAFT doesn't need training (uses pre-trained weights)
- Already configured and ready

### 3. TR-OCR Only (Text Recognition)
```bash
# Same as CRAFT+TR-OCR but only TR-OCR part is trained
python3 backend/training/train_craft_trocr.py \
  training_data/student_forms.json \
  models/trocr_only \
  --epochs 20
```

### 4. Tesseract
- Tesseract uses language data files
- Can train custom language model (advanced)
- Default English model works well

### 5. Google Vision / Azure / AWS
- Cloud providers - no local training needed
- Use their APIs directly

---

## 📊 Training Data Format

```json
[
  {
    "image_path": "data/samples/images/jatin_page_01.png",
    "text": "Extracted text from image...",
    "confidence": 0.85
  }
]
```

---

## ✅ Quick Start

```bash
# 1. Prepare data (if not done)
python3 backend/scripts/prepare_training_from_images_simple.py

# 2. Train CRAFT+TR-OCR
python3 backend/training/train_craft_trocr.py \
  training_data/student_forms.json \
  models/trocr_student_forms \
  --epochs 20 \
  --batch-size 8

# 3. Use trained model
echo "TROCR_CUSTOM_MODEL_PATH=models/trocr_student_forms" >> .env
```

---

## 🎓 Training Tips

1. **Start with CRAFT+TR-OCR** - Best for handwritten forms
2. **Use 20+ epochs** - Better accuracy
3. **Batch size 8** - Good balance of speed/quality
4. **Monitor training** - Watch loss decrease
5. **Validate** - Check accuracy on validation set

---

**Ready to train!** 🚀
