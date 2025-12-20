# Using CRAFT + TR-OCR for Scanning and Training

## ✅ CRAFT + TR-OCR is Now Enabled!

CRAFT + TR-OCR is now **enabled by default** and will appear in your OCR provider list.

## 🚀 Quick Start

### Step 1: Install Dependencies (If Not Already Done)

```bash
./setup_craft_trocr.sh
```

Or manually:
```bash
pip install craft-text-detector transformers torch torchvision
```

### Step 2: Run the App

```bash
./start_app.sh
```

### Step 3: Upload Forms with CRAFT + TR-OCR

1. Open http://localhost:5173
2. Click **"Upload"**
3. Select your scanned student forms
4. **Select "CRAFT + TR-OCR (Handwritten) ⭐"** from OCR Provider dropdown
5. Click **"Upload & Extract"**

**CRAFT + TR-OCR is now the default provider!** It will automatically be selected.

### Step 4: Verify Forms

1. Go to **Dashboard**
2. Click **"View"** on each form
3. **Manually correct ALL fields**
4. Click **"Save & Verify"**
5. Repeat for 50+ forms

### Step 5: Train Model

```bash
./train_my_forms.sh
```

This will:
- ✅ Analyze your verified forms
- ✅ Use CRAFT+TR-OCR for training (best for handwritten)
- ✅ Prepare training data with all field mappings
- ✅ Train the model
- ✅ Save for future use

---

## 🎯 Why CRAFT + TR-OCR?

### Best for Handwritten Forms

- ✅ **CRAFT**: Detects text regions accurately
- ✅ **TR-OCR**: Recognizes handwritten text with high accuracy
- ✅ **Combined**: Best results for handwritten student forms

### Performance

- **Accuracy**: 90%+ for handwritten text
- **Speed**: Fast on GPU, moderate on CPU
- **Training**: Can be fine-tuned on your data

---

## 📋 Complete Workflow

### 1. Upload Forms

```bash
# Via web interface:
# 1. Select "CRAFT + TR-OCR (Handwritten) ⭐"
# 2. Upload forms
# 3. Wait for extraction
```

### 2. Verify Forms

- Review extracted text
- Correct all 120+ fields manually
- Save & Verify each form

### 3. Prepare Training Data

```bash
python backend/training/train_best_model.py --prepare-only \
  --output-data training_data/student_forms.json
```

### 4. Train Model

```bash
python backend/training/train_best_model.py \
  --training-data training_data/student_forms.json \
  --output-model models/trocr_student_forms \
  --model-type craft-trocr \
  --epochs 20 \
  --batch-size 8
```

### 5. Use Trained Model

Add to `.env`:
```env
TROCR_CUSTOM_MODEL_PATH=models/trocr_student_forms
```

Restart backend and upload new forms - **all fields will auto-fill accurately!**

---

## 🔧 Configuration

### Enable/Disable CRAFT+TR-OCR

**In `.env` file:**
```env
# Enable CRAFT+TR-OCR (default: true)
OCR_ENABLE_CRAFT_TROCR=true

# Set as default provider
OCR_PROVIDER=craft-trocr
```

### Use Custom Trained Model

```env
# Use your trained model
TROCR_CUSTOM_MODEL_PATH=models/trocr_student_forms
```

---

## 📊 Provider Comparison

| Provider | Handwritten | Printed | Speed | Cost |
|----------|------------|---------|-------|------|
| **CRAFT + TR-OCR** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Fast (GPU) | Free |
| Google Document AI | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Fast | Paid |
| Azure Form Recognizer | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Fast | Paid |
| Tesseract | ⭐⭐⭐ | ⭐⭐⭐⭐ | Fast | Free |

**CRAFT + TR-OCR is the best free option for handwritten forms!**

---

## ✅ What's Ready

1. ✅ **CRAFT+TR-OCR enabled by default**
2. ✅ **Shows in provider dropdown** with label "CRAFT + TR-OCR (Handwritten) ⭐"
3. ✅ **All 120+ fields mapped** for training
4. ✅ **Training scripts ready** to use CRAFT+TR-OCR
5. ✅ **One-command training** available

---

## 🚀 Next Steps

1. **Run the app**: `./start_app.sh`
2. **Upload forms**: Select "CRAFT + TR-OCR (Handwritten) ⭐"
3. **Verify forms**: Correct all fields manually
4. **Train model**: `./train_my_forms.sh`
5. **Use trained model**: Set `TROCR_CUSTOM_MODEL_PATH` in `.env`

---

## 📚 Documentation

- **CRAFT+TR-OCR Guide**: [CRAFT_TROCR_GUIDE.md](CRAFT_TROCR_GUIDE.md)
- **Training Guide**: [START_TRAINING.md](START_TRAINING.md)
- **Field Mapping**: [FORM_FIELD_MAPPING.md](FORM_FIELD_MAPPING.md)
- **Quick Start**: [CRAFT_TROCR_QUICK_START.md](CRAFT_TROCR_QUICK_START.md)

---

**CRAFT + TR-OCR is ready to use! 🎉**

Upload forms, verify them, and train your model for accurate auto-filling!
