# 🎯 Complete Training Workflow - Test OCR & Train CRAFT+TR-OCR

## ✅ What's Set Up

### 1. Automatic Annotation from Verification ✅
- When you verify a form in the browser, annotations are **automatically created**
- All verified fields become training data
- No manual annotation needed!

### 2. OCR Testing Script ✅
- Test all OCR providers including Ollama
- Compare results from different providers
- Test Ollama with llama3.2-vision specifically

### 3. Training Data Preparation ✅
- Automatically extracts training data from verified forms
- Converts annotations to CRAFT+TR-OCR format
- Ready for training

### 4. Complete Training Pipeline ✅
- CRAFT+TR-OCR training script ready
- Browser-based training interface
- CLI training option

---

## 🚀 Quick Start Workflow

### Step 1: Test OCR Providers (Including Ollama)

```bash
# Test Ollama specifically
python3 test_ocr_providers.py data/samples/images/jatin_page_01.png --ollama-only

# Test all providers
python3 test_ocr_providers.py data/samples/images/jatin_page_01.png --all
```

### Step 2: Verify Forms in Browser

1. Go to http://localhost:5173
2. Upload forms
3. Click on each form
4. **Correct any errors** in the fields
5. Click **"Save Verification"** or **"Update Form"**
6. **Annotations are automatically created!** ✅

### Step 3: Prepare Training Data

```bash
# Prepare training data from verified forms
python3 prepare_training_from_annotations.py
```

This will:
- Find all verified forms with annotations
- Extract images and ground truth text
- Create training data in CRAFT+TR-OCR format
- Save to `training_data/annotated_forms_training.json`

### Step 4: Train CRAFT+TR-OCR

**Option 1: Via Browser** (Recommended)
1. Go to http://localhost:5173/training
2. Click "Prepare Training Data" (if needed)
3. Click "Start Training CRAFT+TR-OCR"

**Option 2: Via CLI**
```bash
python3 backend/training/train_craft_trocr.py \
  training_data/annotated_forms_training.json \
  models/trocr_trained \
  --epochs 20 \
  --batch-size 8 \
  --image-dir .
```

### Step 5: Use Trained Model

```bash
# Update .env
echo "TROCR_CUSTOM_MODEL_PATH=models/trocr_trained" >> .env

# Restart backend
```

---

## 🧪 Complete Test & Train Workflow

Run the complete workflow script:

```bash
./test_and_train_workflow.sh
```

This will:
1. ✅ Check Ollama installation and llama3.2-vision model
2. ✅ Test OCR providers (including Ollama)
3. ✅ Check annotated forms
4. ✅ Prepare training data
5. ✅ Train CRAFT+TR-OCR (if enough samples)

---

## 📋 Detailed Steps

### 1. Test Ollama with llama3.2-vision

**Check Ollama:**
```bash
# Check if Ollama is installed
ollama --version

# Check if model is available
ollama list

# If not, pull the model
ollama pull llama3.2-vision

# Start Ollama (if not running)
ollama serve
```

**Test Ollama OCR:**
```bash
python3 test_ocr_providers.py data/samples/images/jatin_page_01.png --ollama-only
```

### 2. Verify Forms to Create Annotations

**In Browser:**
1. Upload form → http://localhost:5173/upload
2. Open form → Click on it
3. Review and correct fields
4. Save verification
5. **Annotation automatically created!** ✅

**Check Annotations:**
```bash
python3 -c "
from backend.database import SessionLocal, AdmissionForm
db = SessionLocal()
forms = db.query(AdmissionForm).filter(
    AdmissionForm.status == 'verified'
).all()
annotated = [f for f in forms if f.additional_info and 'annotation' in f.additional_info]
print(f'Annotated forms: {len(annotated)}')
for f in annotated[:5]:
    fields = f.additional_info['annotation'].get('key_value_pairs', {})
    print(f'  Form {f.id}: {len(fields)} fields')
db.close()
"
```

### 3. Prepare Training Data

```bash
python3 prepare_training_from_annotations.py
```

**Output:**
- `training_data/annotated_forms_training.json`
- Format: `{"image_path": "...", "text": "ground truth text"}`

### 4. Train CRAFT+TR-OCR

**Minimum Requirements:**
- 10+ annotated forms (recommended: 50+)
- Each form should have verified/corrected data

**Training:**
```bash
python3 backend/training/train_craft_trocr.py \
  training_data/annotated_forms_training.json \
  models/trocr_trained \
  --epochs 20 \
  --batch-size 8 \
  --image-dir . \
  --base-model microsoft/trocr-base-handwritten
```

**Training Time:**
- 10-20 samples: 30-60 minutes
- 50+ samples: 2-4 hours
- 100+ samples: 4-8 hours

### 5. Use Trained Model

After training completes:

```bash
# Update .env
echo "TROCR_CUSTOM_MODEL_PATH=models/trocr_trained" >> .env

# Restart backend
# The trained model will be used automatically
```

---

## 🎯 Workflow Summary

```
1. Test OCR (including Ollama)
   ↓
2. Upload & Verify Forms (creates annotations automatically)
   ↓
3. Prepare Training Data (from annotations)
   ↓
4. Train CRAFT+TR-OCR
   ↓
5. Use Trained Model
```

---

## ✅ Verification Checklist

- [ ] Ollama installed and running
- [ ] llama3.2-vision model pulled
- [ ] OCR providers tested (including Ollama)
- [ ] Forms uploaded and verified (creates annotations)
- [ ] Training data prepared
- [ ] CRAFT+TR-OCR trained
- [ ] Trained model configured in .env

---

## 🐛 Troubleshooting

### Ollama Not Working
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama
ollama serve

# Pull model if missing
ollama pull llama3.2-vision
```

### No Annotations Found
- Make sure you've verified forms (not just uploaded)
- Check: Forms must have status='verified' and annotations in additional_info
- Verify a form in browser to create annotation

### Training Fails
- Check PyTorch version: `python3 -c "import torch; print(torch.__version__)"`
- Need PyTorch >= 2.1
- Check training data format: `cat training_data/annotated_forms_training.json | head -20`

---

## 📊 Expected Results

### After Verification
- Each verified form has annotation in `additional_info.annotation`
- Key-value pairs extracted from verified fields
- Ready for training data preparation

### After Training Data Preparation
- JSON file with image paths and ground truth text
- One entry per verified form
- Format compatible with CRAFT+TR-OCR

### After Training
- Trained model in `models/trocr_trained/`
- Improved accuracy on your specific forms
- Can be used as custom model

---

**Ready to test OCR and train!** 🚀

Run `./test_and_train_workflow.sh` to start!
