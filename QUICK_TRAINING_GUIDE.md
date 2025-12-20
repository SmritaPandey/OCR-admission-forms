# Quick Training Guide - Train Best Model for Your Forms

## 🎯 Goal

Train the **best OCR model** (CRAFT+TR-OCR, Tesseract, or combo) to automatically fill all student form fields accurately.

## ⚡ One-Command Training

After verifying 50+ forms, simply run:

```bash
./train_my_forms.sh
```

This will:
1. ✅ Analyze your verified forms
2. ✅ Determine best model (CRAFT+TR-OCR for handwritten)
3. ✅ Prepare training data with field mappings
4. ✅ Train the optimal model
5. ✅ Save model for future use

## 📋 Step-by-Step Process

### Step 1: Upload and Verify Forms (Week 1-2)

1. **Run the app:**
   ```bash
   ./start_app.sh
   ```

2. **Upload forms:**
   - Go to http://localhost:5173
   - Click "Upload"
   - Select scanned forms
   - Use **CRAFT + TR-OCR** for handwritten forms

3. **Verify forms:**
   - Go to Dashboard
   - Click "View" on each form
   - **Manually correct ALL 40+ fields**
   - Click "Save & Verify"
   - Repeat for **50+ forms** (minimum)

### Step 2: Analyze Forms

```bash
python backend/training/train_best_model.py --analyze-only
```

**Output:**
```
Analysis Results:
  Total forms: 75
  Handwritten ratio: 68.0%
  Average confidence: 72.3%
  Best provider: craft-trocr

Recommendation: craft-trocr
Reason: High handwritten text ratio (68.0%). CRAFT+TR-OCR is best for handwritten forms.
```

### Step 3: Prepare Training Data

```bash
python backend/training/train_best_model.py --prepare-only \
  --output-data training_data/student_forms.json
```

**What this does:**
- Extracts verified forms from database
- Creates field mappings (label → value pairs)
- Maps OCR text to structured fields
- Saves in training format

### Step 4: Train Model

```bash
python backend/training/train_best_model.py \
  --training-data training_data/student_forms.json \
  --output-model models/trocr_student_forms \
  --epochs 20 \
  --batch-size 8
```

**Training time:**
- GPU: ~1-2 hours
- CPU: ~6-12 hours
- Apple Silicon: ~3-6 hours

### Step 5: Use Trained Model

**Add to `.env` file:**
```env
TROCR_CUSTOM_MODEL_PATH=models/trocr_student_forms
```

**Or set environment variable:**
```bash
export TROCR_CUSTOM_MODEL_PATH="models/trocr_student_forms"
```

**Restart backend:**
```bash
# Stop backend (Ctrl+C)
python -m uvicorn backend.main:app --reload --port 8000
```

**Now upload new forms:**
- Select **CRAFT + TR-OCR** as OCR provider
- Your trained model will be used automatically
- Fields will auto-fill accurately! 🎉

---

## 🗺️ Field Mapping System

The system automatically maps OCR text to form fields:

### How It Works

1. **OCR extracts text** from form
2. **Field mapper** searches for label patterns:
   - "Student Name" → `student_name`
   - "Date of Birth" → `date_of_birth`
   - "Phone" → `phone_number`
   - etc.
3. **Extracts values** using regex patterns
4. **Maps to structured fields** automatically
5. **Training learns** these mappings

### All 40+ Fields Mapped

**Basic Details:**
- Student Name, DOB, Gender, Category, Nationality, Religion, Aadhar, Blood Group

**Address:**
- Permanent Address, Correspondence Address, City, State, Pincode

**Contact:**
- Phone, Alternate Phone, Email, Emergency Contact

**Parent/Guardian:**
- Father/Mother/Guardian Name, Occupation, Phone, Annual Income

**Education:**
- 10th/12th Board, Year, Percentage, School
- Previous Qualification, Graduation Details

**Course:**
- Course Applied, Application Number, Enrollment Number, Admission Date

---

## 🎯 Model Selection

The system automatically recommends the best model:

### CRAFT + TR-OCR (Recommended)
- **Best for:** Handwritten forms (70%+ handwritten)
- **Accuracy:** Highest for handwritten text
- **Training:** Requires GPU for fast training

### Tesseract
- **Best for:** Printed forms
- **Accuracy:** Good for printed text
- **Training:** Works on CPU

### Auto Selection
The script analyzes your forms and chooses automatically:
- High handwritten ratio → CRAFT+TR-OCR
- Low confidence → CRAFT+TR-OCR
- Good printed text → Tesseract

---

## ✅ Success Checklist

Before training:
- [ ] 50+ verified forms in database
- [ ] All forms have 5+ verified fields
- [ ] Forms are clear and readable
- [ ] Student Name is filled (required)

After training:
- [ ] Model saved successfully
- [ ] Environment variable set
- [ ] Backend restarted
- [ ] Test on new form
- [ ] Fields auto-fill correctly

---

## 🔄 Continuous Improvement

### Retrain After More Forms

After verifying 50+ more forms:

```bash
# Prepare new data
python backend/training/train_best_model.py --prepare-only

# Retrain
python backend/training/train_best_model.py \
  --training-data training_data/student_forms.json \
  --output-model models/trocr_student_forms_v2 \
  --epochs 15
```

### Monitor Performance

- Track field accuracy on new forms
- Identify common errors
- Add more training data for problematic fields

---

## 🐛 Troubleshooting

### "No verified forms found"

**Solution:**
- Verify forms in the web interface first
- Check database has forms with status="verified"
- Ensure forms have 5+ verified fields

### "Training data preparation failed"

**Solution:**
- Check image files exist in uploads/
- Verify forms have extracted_data
- Ensure verified fields are filled

### "Model training failed"

**Solution:**
- Check GPU/CPU availability
- Reduce batch size if out of memory
- Use fewer epochs for testing
- Check training data format

---

## 📊 Expected Results

After training, you should see:

- ✅ **CER < 0.1** (90%+ character accuracy)
- ✅ **WER < 0.3** (70%+ word accuracy)
- ✅ **Field accuracy > 85%** (most fields correct)
- ✅ **Auto-fill works** for 80%+ of fields

---

## 🚀 Quick Commands

### Analyze Only
```bash
python backend/training/train_best_model.py --analyze-only
```

### Prepare Data Only
```bash
python backend/training/train_best_model.py --prepare-only \
  --output-data training_data/student_forms.json
```

### Train Only
```bash
python backend/training/train_best_model.py \
  --training-data training_data/student_forms.json \
  --output-model models/trocr_student_forms \
  --epochs 20
```

### Everything (One Command)
```bash
./train_my_forms.sh
```

---

## 📚 Documentation

- **Complete Workflow**: [COMPLETE_TRAINING_WORKFLOW.md](COMPLETE_TRAINING_WORKFLOW.md)
- **Field Mappings**: `backend/training/field_mapper.py`
- **Training Script**: `backend/training/train_best_model.py`
- **TR-OCR Training**: [PERFECT_TRAINING_GUIDE.md](PERFECT_TRAINING_GUIDE.md)

---

**You're ready to train the perfect model! 🎓**

1. Upload and verify 50+ forms
2. Run `./train_my_forms.sh`
3. Use trained model for accurate auto-filling!
