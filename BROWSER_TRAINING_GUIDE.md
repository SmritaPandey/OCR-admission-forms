# 🚀 Browser-Based Training Guide

## ✅ Training Interface Ready!

A **Training Interface** has been added to the web application!

### Access Training Interface

1. **Start the app** (if not running):
   ```bash
   ./start_app.sh
   ```

2. **Navigate to Training**:
   - Go to http://localhost:5173
   - Click **"Training"** in the navigation menu
   - Or go directly to: http://localhost:5173/training

---

## 🎯 Training Workflow in Browser

### Step 1: Prepare Training Data
- Click **"Prepare Training Data"** button
- This extracts training data from verified forms
- Shows statistics about available data

### Step 2: Configure Training
- **Model Type**: TR-OCR (Handwritten Text Recognition)
- **Epochs**: 20 (recommended)
- **Batch Size**: 8 (adjust based on GPU memory)
- **Learning Rate**: 5e-5 (default)

### Step 3: Start Training
- Click **"Start Training CRAFT+TR-OCR"**
- Training runs in background
- Check terminal/console for progress

---

## 📊 Current Training Data

- **20 samples** ready in `training_data/student_forms.json`
- **185 images** available in `data/samples/images/`
- Can process more images to increase training data

---

## 🎓 Training CRAFT+TR-OCR (Best Pipeline)

### Via Browser (Recommended)
1. Go to http://localhost:5173/training
2. Click "Prepare Training Data" (if needed)
3. Configure training settings
4. Click "Start Training CRAFT+TR-OCR"

### Via Command Line
```bash
# Quick training (20 samples)
python3 backend/training/train_craft_trocr.py \
  training_data/student_forms.json \
  models/trocr_student_forms \
  --epochs 20 \
  --batch-size 8 \
  --image-dir .

# Full training (all 185 images)
./train_all_providers.sh
```

---

## ✅ After Training

1. **Model Location**: `models/trocr_student_forms/`
2. **Update .env**:
   ```env
   TROCR_CUSTOM_MODEL_PATH=models/trocr_student_forms
   ```
3. **Restart Backend**
4. **Test**: Upload a form - improved accuracy!

---

## 🎯 Training All Providers

### 1. CRAFT+TR-OCR ⭐ (Best Pipeline)
- **Via Browser**: http://localhost:5173/training
- **Via CLI**: `./train_all_providers.sh`

### 2. CRAFT Only
- Uses pre-trained weights
- No training needed
- Ready to use

### 3. TR-OCR Only
- Same as CRAFT+TR-OCR
- Only TR-OCR part is fine-tuned

### 4. Other Providers
- Tesseract: Uses default models
- Google/Azure/AWS: Cloud-based, no local training

---

## 📋 Training Data Status

**Current**: 20 samples with real OCR text
**Available**: 185 images ready for processing
**Location**: `training_data/student_forms.json`

---

## 🚀 Quick Start

1. **Open Browser**: http://localhost:5173/training
2. **Prepare Data**: Click "Prepare Training Data"
3. **Configure**: Set epochs=20, batch_size=8
4. **Train**: Click "Start Training CRAFT+TR-OCR"
5. **Wait**: Training runs in background (1-6 hours)
6. **Use**: Update .env and restart backend

---

**Training interface is ready! Open http://localhost:5173/training to start!** 🎉
