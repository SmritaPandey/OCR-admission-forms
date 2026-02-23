# Start Training - Complete Guide

## 🎯 Your Goal

Train the **best OCR model** (CRAFT+TR-OCR, Tesseract, or combo) to automatically extract and fill **ALL 120+ fields** from your student admission forms.

## ✅ What's Been Done

I've mapped **ALL fields** from your form images:

- ✅ **120+ fields** mapped with label patterns
- ✅ **Field mapper** updated with all form fields
- ✅ **Training scripts** ready to use
- ✅ **Field extraction** handles all fields

## 🚀 Complete Workflow

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
3. Upload your scanned student forms (PDF or images)
4. Select **CRAFT + TR-OCR** for handwritten forms
5. Wait for OCR extraction

### Step 3: Verify ALL Fields

1. Go to **Dashboard**
2. Click **"View"** on each form
3. **Manually correct ALL 120+ fields** in the verification form:
   - Academic & Admission (8 fields)
   - Name Fields (4 fields)
   - Personal Details (10 fields)
   - Address Details (10 fields)
   - Contact Details (3 fields)
   - Parent/Guardian (20 fields)
   - Educational (10 fields)
   - CUET Marks (19 fields)
   - Occupational (14 fields)
   - Documents (15 fields)
   - Declarations (7 fields)
   - Other (10 fields)
4. Click **"Save & Verify"**
5. Repeat for **50+ forms** (minimum for training)

**Important:** Verify as many fields as possible for each form. More verified fields = better training!

### Step 4: Prepare Training Data

```bash
python backend/training/train_best_model.py --prepare-only \
  --output-data training_data/student_forms.json \
  --limit 100
```

**What this does:**
- ✅ Extracts verified forms from database
- ✅ Maps OCR text to all 120+ fields
- ✅ Creates field mappings (label → value pairs)
- ✅ Saves training data in JSON format

**Output:**
```
✅ Processed: 75 forms
✅ With field mappings: 75 forms
📁 Saved to: training_data/student_forms.json
```

### Step 5: Analyze Forms (Optional)

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

### Step 6: Train the Model

```bash
python backend/training/train_best_model.py \
  --training-data training_data/student_forms.json \
  --output-model models/trocr_student_forms \
  --model-type craft-trocr \
  --epochs 20 \
  --batch-size 8
```

**Or use the one-command script:**
```bash
./train_my_forms.sh
```

**Training time:**
- **GPU**: ~1-2 hours for 75 forms
- **CPU**: ~6-12 hours
- **Apple Silicon (MPS)**: ~3-6 hours

### Step 7: Use Trained Model

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
- **All 120+ fields will auto-fill accurately!** 🎉

---

## 📋 All 120+ Fields Mapped

### Academic & Admission (8 fields)
- Academic Session, Course, Admission Category, DU Portal Form Number
- CUET Score, College Roll No., Date of Admission

### Name Fields (4 fields)
- First Name, Middle Name, Surname, Student Name (combined)

### Personal Details (10 fields)
- Date of Birth, Gender, Category, Nationality, Religion
- Aadhar Number, Blood Group, Below Poverty Line, Annual Income, Minority Category

### Address Details (10 fields)
- Permanent Address (3 lines), Permanent State, Permanent PIN
- Correspondence Address (3 lines), Correspondence State, Correspondence PIN

### Contact Details (3 fields)
- Phone Number, Alternate Phone, Email

### Parent/Guardian Details (20 fields)
- Father: Name, Occupation, Designation, Organization, Email, Mobile, Landline
- Mother: Name, Occupation, Designation, Organization, Email, Mobile, Landline
- Guardian: Name, Relation, Residential Address, Organization, Email, Mobile, Landline

### Educational Qualifications (10 fields)
- 10th: Board, Year, Percentage, School
- 12th: Board, Year, Roll Number, Institution, Percentage, School, Hindi Studied Upto

### CUET Marks (19 fields)
- 6 Subjects: Subject Name, Total Score, Score Obtained (each)
- Total CUET Score

### Occupational Details (14 fields)
- Mother's/Father's/Guardian's: Occupation, Designation, Organization, Email, Mobile, Landline Code, Landline

### Documents Checklist (15 fields)
- All document checkboxes (attached/not attached)

### Declarations (7 fields)
- Student: Name, Date, Place, Signature
- Parent/Guardian: Name, Relationship, Candidate Name, Course, Date, Place, Signature

### Other (10 fields)
- DU Enrollment Number, Hindi Medium Preference
- Category Certificate: Authority, Number, Date
- Disability: Percentage, Type, UDID Number

---

## 🗺️ Field Mapping Examples

### Example 1: Name Extraction

**Form Label:** "NAME IN BLOCK LETTERS"
**OCR Text:** "First Name: JOHN\nMiddle Name: DOE\nSurname: SMITH"

**Mapped:**
```json
{
  "first_name": "JOHN",
  "middle_name": "DOE",
  "surname": "SMITH",
  "student_name": "JOHN DOE SMITH"
}
```

### Example 2: CUET Marks Table

**Form Label:** "Details of marks obtained in Qualifying Examination: [CUET]"
**OCR Text:** "ENGLISH | 200 | 185\nMATHEMATICS | 200 | 190"

**Mapped:**
```json
{
  "cuet_subject_1": "ENGLISH",
  "cuet_total_score_1": "200",
  "cuet_score_obtained_1": "185",
  "cuet_subject_2": "MATHEMATICS",
  "cuet_total_score_2": "200",
  "cuet_score_obtained_2": "190"
}
```

### Example 3: Occupational Details

**Form Label:** "Father's Occupational Details"
**OCR Text:** "Occupation: ENGINEER\nMobile No.: 9876543210\nCode: 011\nLandline No.: 12345678"

**Mapped:**
```json
{
  "father_occupation": "ENGINEER",
  "father_mobile": "9876543210",
  "father_landline_code": "011",
  "father_landline": "12345678"
}
```

---

## ✅ Quality Checklist

Before training, ensure:

- [ ] **50+ verified forms** in database
- [ ] **Each form has 10+ verified fields** (more is better)
- [ ] **All fields are accurate** (manually verified)
- [ ] **Forms are clear and readable**
- [ ] **Student Name is filled** (required)

---

## 🎯 Expected Results

After training, you should see:

- ✅ **CER < 0.1** (90%+ character accuracy)
- ✅ **WER < 0.3** (70%+ word accuracy)
- ✅ **Field accuracy > 85%** (most fields correct)
- ✅ **Auto-fill works** for 80%+ of fields
- ✅ **All 120+ fields** can be extracted

---

## 📚 Documentation

- **Field Mapping**: [FORM_FIELD_MAPPING.md](FORM_FIELD_MAPPING.md) - All fields listed
- **Complete Guide**: [COMPLETE_FIELD_MAPPING_GUIDE.md](COMPLETE_FIELD_MAPPING_GUIDE.md) - Detailed mapping
- **Training Workflow**: [COMPLETE_TRAINING_WORKFLOW.md](COMPLETE_TRAINING_WORKFLOW.md) - Full process
- **Quick Guide**: [QUICK_TRAINING_GUIDE.md](QUICK_TRAINING_GUIDE.md) - Quick reference

---

## 🚀 Quick Commands

### One-Command Training
```bash
./train_my_forms.sh
```

### Step-by-Step
```bash
# 1. Prepare data
python backend/training/train_best_model.py --prepare-only

# 2. Train model
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

## 🎉 You're Ready!

1. ✅ **All 120+ fields mapped**
2. ✅ **Field mapper updated**
3. ✅ **Training scripts ready**
4. ✅ **One-command training available**

**Next:** Upload forms, verify them, and train your model!

---

**All fields are mapped and ready for training! 🎓**

For field details, see [FORM_FIELD_MAPPING.md](FORM_FIELD_MAPPING.md)
