# Complete Training Workflow - Best Model for Student Forms

## 🎯 Overview

This guide helps you:
1. **Upload and verify** student forms
2. **Analyze** which OCR model works best for your forms
3. **Train** the optimal model (CRAFT+TR-OCR, Tesseract, or combo)
4. **Auto-fill** all form fields accurately

## 🚀 Quick Start

### Step 1: Run the App

```bash
./start_app.sh
```

Or manually:
```bash
# Terminal 1: Backend
python -m uvicorn backend.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend && npm run dev
```

### Step 2: Upload Forms

1. Open http://localhost:5173
2. Click **"Upload"**
3. Upload your scanned student forms
4. Use **CRAFT + TR-OCR** for handwritten forms
5. Wait for OCR extraction

### Step 3: Verify Forms

1. Go to **Dashboard**
2. Click **"View"** on each form
3. **Manually correct all fields** in the verification form
4. Click **"Save & Verify"**
5. Repeat for 50+ forms (minimum for training)

### Step 4: Analyze and Train

```bash
# Analyze your forms and train the best model
python backend/training/train_best_model.py \
  --output-data training_data/student_forms.json \
  --output-model models/trocr_student_forms \
  --epochs 20 \
  --batch-size 8
```

This will:
- ✅ Analyze your verified forms
- ✅ Determine best model (CRAFT+TR-OCR recommended for handwritten)
- ✅ Prepare training data with field mappings
- ✅ Train the optimal model
- ✅ Save trained model for future use

---

## 📋 Complete Workflow

### Phase 1: Data Collection (Week 1-2)

**Goal:** Collect 50-100 verified forms

#### Day 1-3: Upload Forms

```bash
# Upload forms via web interface
# Or use API:
curl -X POST http://localhost:8000/api/upload \
  -F "file=@form1.pdf" \
  -F "ocr_provider=craft-trocr"
```

**Tips:**
- Use **CRAFT + TR-OCR** for handwritten forms
- Use **Google Document AI** if available (best accuracy)
- Upload 10-20 forms per day

#### Day 4-10: Verify Forms

1. **Open each form** from Dashboard
2. **Review extracted text**
3. **Manually correct ALL fields:**
   - Basic Details (8 fields)
   - Address Details (5 fields)
   - Contact Details (5 fields)
   - Parent/Guardian (10 fields)
   - Educational Qualifications (12 fields)
   - Course Details (4 fields)
4. **Save & Verify**

**Quality Checklist:**
- [ ] Student Name is correct (required)
- [ ] All dates in DD/MM/YYYY format
- [ ] Phone numbers are 10 digits
- [ ] Email addresses are valid
- [ ] Addresses are complete
- [ ] Educational details match the form
- [ ] All handwritten text correctly transcribed

### Phase 2: Analysis (Day 11)

**Analyze your forms to determine best model:**

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

### Phase 3: Prepare Training Data (Day 12)

**Prepare training data with field mappings:**

```bash
python backend/training/train_best_model.py --prepare-only \
  --output-data training_data/student_forms.json \
  --limit 100
```

**What this does:**
- ✅ Extracts verified forms from database
- ✅ Creates field mappings (label → value pairs)
- ✅ Maps OCR text to structured fields
- ✅ Saves training data in JSON format

**Output:**
```
✅ Processed: 75 forms
✅ With field mappings: 75 forms
📁 Saved to: training_data/student_forms.json
```

### Phase 4: Train Model (Day 13-14)

**Train the best model:**

```bash
python backend/training/train_best_model.py \
  --training-data training_data/student_forms.json \
  --output-model models/trocr_student_forms \
  --model-type craft-trocr \
  --epochs 20 \
  --batch-size 8
```

**Training time:**
- **GPU**: ~1-2 hours for 75 forms
- **CPU**: ~6-12 hours
- **Apple Silicon (MPS)**: ~3-6 hours

**Monitor training:**
- Watch for decreasing loss
- Check validation metrics (CER, WER)
- Training saves checkpoints automatically

### Phase 5: Use Trained Model (Day 15+)

**Set environment variable:**

```bash
export TROCR_CUSTOM_MODEL_PATH="models/trocr_student_forms"
```

**Or update `.env` file:**
```env
TROCR_CUSTOM_MODEL_PATH=models/trocr_student_forms
```

**Restart backend:**
```bash
# Stop backend (Ctrl+C)
# Start again
python -m uvicorn backend.main:app --reload --port 8000
```

**Now upload new forms:**
- Select **CRAFT + TR-OCR** as OCR provider
- Your trained model will be used automatically
- Fields will auto-fill more accurately!

---

## 🗺️ Field Mapping System

The system automatically maps OCR text to form fields using pattern matching:

### Field Mappings

**Basic Details:**
- `student_name` → "Student Name", "Name", "Applicant Name"
- `date_of_birth` → "Date of Birth", "DOB", "Birth Date"
- `gender` → "Gender", "Sex"
- `category` → "Category", "Caste Category"
- `aadhar_number` → "Aadhar", "Aadhaar", "UID"
- `blood_group` → "Blood Group", "Blood Type"

**Address:**
- `permanent_address` → "Permanent Address", "Address"
- `correspondence_address` → "Correspondence Address", "Mailing Address"
- `city` → "City", "Town"
- `state` → "State", "Province"
- `pincode` → "Pincode", "Pin Code", "Postal Code"

**Contact:**
- `phone_number` → "Phone", "Mobile", "Contact Number"
- `email` → "Email", "E-mail", "Email Address"

**Education:**
- `tenth_board` → "10th Board", "Tenth Board", "SSC Board"
- `tenth_percentage` → "10th Percentage", "10th %"
- `twelfth_board` → "12th Board", "Twelfth Board", "HSC Board"
- `twelfth_percentage` → "12th Percentage", "12th %"

**Course:**
- `course_applied` → "Course Applied", "Course", "Program"
- `application_number` → "Application Number", "Application No"
- `enrollment_number` → "Enrollment Number", "Enrollment No"

### How It Works

1. **OCR extracts text** from form image
2. **Field mapper** searches for label patterns
3. **Extracts values** using regex patterns
4. **Maps to structured fields** automatically
5. **Training uses mappings** to learn field recognition

---

## 🎯 Training Data Format

Training data includes:

```json
{
  "image_path": "uploads/training_images/form_1_page1.png",
  "text": "Student Name: John Doe\nDate of Birth: 01/01/2000\n...",
  "verified_fields": {
    "student_name": "John Doe",
    "date_of_birth": "01/01/2000",
    ...
  },
  "field_mappings": [
    {
      "field_key": "student_name",
      "label": "student name",
      "value": "John Doe",
      "extracted_value": "John Doe",
      "field_type": "text"
    },
    ...
  ]
}
```

---

## 📊 Model Comparison

### CRAFT + TR-OCR (Recommended for Handwritten)

**Best for:**
- ✅ Handwritten forms (70%+ handwritten text)
- ✅ Medical prescriptions
- ✅ Forms with varied handwriting styles
- ✅ Low confidence OCR results

**Training:**
- Requires GPU for fast training
- ~1-2 hours for 100 forms (GPU)
- Best accuracy for handwritten text

### Tesseract (Good for Printed)

**Best for:**
- ✅ Printed forms
- ✅ High-quality scans
- ✅ Forms with consistent fonts
- ✅ Limited training data

**Training:**
- Faster training (CPU is fine)
- ~30-60 minutes for 100 forms
- Good for printed text

### Combo Approach

**Use both:**
1. Train CRAFT+TR-OCR for handwritten sections
2. Train Tesseract for printed sections
3. Combine results intelligently

---

## ✅ Success Criteria

Your model is ready when:

- ✅ **CER < 0.1** (90%+ character accuracy)
- ✅ **WER < 0.3** (70%+ word accuracy)
- ✅ **Field accuracy > 85%** (most fields correct)
- ✅ **Auto-fill works** for 80%+ of fields

---

## 🔄 Continuous Improvement

### Retrain Periodically

After verifying 50+ more forms:

```bash
# Prepare new training data
python backend/training/train_best_model.py --prepare-only

# Retrain model
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

### Problem: Low training accuracy

**Solutions:**
- Use more training data (100+ forms)
- Train for more epochs (30-50)
- Check data quality (accurate verification)
- Use GPU for training

### Problem: Fields not auto-filling

**Solutions:**
- Verify field mappings are correct
- Check OCR text quality
- Update field mapper patterns
- Retrain with more examples

### Problem: Model not loading

**Solutions:**
- Check model path is correct
- Verify environment variable is set
- Restart backend server
- Check model files exist

---

## 📚 Quick Reference

### Analyze Forms
```bash
python backend/training/train_best_model.py --analyze-only
```

### Prepare Data
```bash
python backend/training/train_best_model.py --prepare-only \
  --output-data training_data/student_forms.json
```

### Train Model
```bash
python backend/training/train_best_model.py \
  --training-data training_data/student_forms.json \
  --output-model models/trocr_student_forms \
  --epochs 20
```

### Use Trained Model
```bash
export TROCR_CUSTOM_MODEL_PATH="models/trocr_student_forms"
# Restart backend
```

---

## 🎉 Next Steps

1. ✅ **Upload 50+ forms** and verify them
2. ✅ **Run analysis** to determine best model
3. ✅ **Prepare training data** with field mappings
4. ✅ **Train the model** (CRAFT+TR-OCR recommended)
5. ✅ **Use trained model** for future forms
6. ✅ **Enjoy accurate auto-filling!** 🚀

---

**You're ready to train the perfect model for your student forms!** 🎓

For detailed field mapping, see `backend/training/field_mapper.py`
