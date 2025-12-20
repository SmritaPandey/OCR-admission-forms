# Run App and Verify Student Forms - Complete Guide

## 🚀 Quick Start - Run the Application

### Step 1: Start Backend Server

Open Terminal 1:

```bash
# Navigate to project directory
cd /Users/smrita/Documents/Projects/OCR-admission-forms

# Start backend server
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

**Wait for:** `Application startup complete` message

Backend will be available at: **http://localhost:8000**

### Step 2: Start Frontend

Open Terminal 2:

```bash
# Navigate to frontend directory
cd /Users/smrita/Documents/Projects/OCR-admission-forms/frontend

# Start frontend development server
npm run dev
```

**Wait for:** `Local: http://localhost:5173` message

Frontend will be available at: **http://localhost:5173**

### Step 3: Open the Application

Open your browser and go to: **http://localhost:5173**

---

## 📤 Step-by-Step: Upload and Verify Forms

### 1. Upload a Scanned Form

1. **Click "Upload"** in the navigation menu
2. **Click "Choose File"** and select your scanned student admission form
   - Supported formats: PDF, JPG, PNG, TIFF, BMP
   - Recommended: PDF or high-quality JPG (300+ DPI)
3. **Select OCR Provider:**
   - **Tesseract** (Free, good for printed text)
   - **CRAFT + TR-OCR** (Best for handwritten text) ⭐
   - **Google Document AI** (Best for handwriting, requires setup)
   - **Azure Form Recognizer** (Best for structured forms)
4. **Click "Upload Form"**
5. Wait for OCR extraction to complete (usually 5-30 seconds)

### 2. View and Verify Form

After upload, you'll be redirected to the **Dashboard**. 

1. **Find your uploaded form** in the list
2. **Click "View"** button on the form
3. You'll see the **Verification View** with:
   - **Left side**: Scanned form image
   - **Right side**: Extracted text and editable form fields

### 3. Review Extracted Text

In the **"Extracted Text (Raw)"** section:
- Review the raw OCR output
- Check if text was extracted correctly
- Note any missing or incorrect text

**If extraction is poor:**
- Click **"Run OCR"** button to try a different OCR provider
- Select **"CRAFT + TR-OCR"** for handwritten text
- Or try **"Google Document AI"** for better accuracy

### 4. Auto-Fill Fields (Optional)

1. Click **"🔄 Auto-fill Fields"** button
2. This attempts to automatically extract field values from the raw text
3. Review and correct as needed

### 5. Manually Correct All Fields

The form has **5 main sections** with **40+ fields**:

#### ✅ Basic Details Section
- **Student Name** * (Required)
- Date of Birth
- Gender (Male/Female/Other)
- Category (General/OBC/SC/ST)
- Nationality
- Religion
- Aadhar Number
- Blood Group (A+, A-, B+, B-, AB+, AB-, O+, O-)

#### ✅ Address Details Section
- Permanent Address
- Correspondence Address
- City
- State
- Pincode

#### ✅ Contact Details Section
- Phone Number
- Alternate Phone
- Email
- Emergency Contact Name
- Emergency Contact Phone

#### ✅ Parent/Guardian Details Section
- Father Name
- Father Occupation
- Father Phone
- Mother Name
- Mother Occupation
- Mother Phone
- Guardian Name
- Guardian Relation
- Guardian Phone
- Annual Income

#### ✅ Educational Qualifications Section
- **10th Standard:**
  - 10th Board
  - 10th Year
  - 10th Percentage
  - 10th School
- **12th Standard:**
  - 12th Board
  - 12th Year
  - 12th Percentage
  - 12th School
- Previous Qualification
- Graduation Details

#### ✅ Course Application Details Section
- Course Applied
- Application Number
- Enrollment Number
- Admission Date

### 6. Verify All Information

**Before saving, verify:**
- ✅ All fields are filled correctly
- ✅ Student Name is entered (required)
- ✅ Dates are in correct format (DD/MM/YYYY)
- ✅ Phone numbers are correct
- ✅ Addresses are complete
- ✅ Educational details are accurate

### 7. Save and Verify

1. **Scroll to bottom** of the form
2. **Click "Save & Verify"** button
3. Form status changes to **"Verified"**
4. You'll be redirected to the Dashboard

**Note:** You can also click **"Update"** to save changes without verifying.

---

## 🔄 Re-Extract with Different OCR Provider

If the initial OCR extraction is poor:

1. **In Verification View**, look for the **"Switch provider"** dropdown
2. **Select a different provider:**
   - **CRAFT + TR-OCR**: Best for handwritten text
   - **Google Document AI**: Excellent for handwriting
   - **Azure Form Recognizer**: Good for structured forms
   - **Tesseract**: Free, good for printed text
3. **Click "Run OCR"** button
4. Wait for re-extraction
5. Review new results and correct fields

---

## 📋 Complete Workflow Example

### Day 1: Upload Forms

1. **Upload 10-20 forms** via the Upload page
2. Use **CRAFT + TR-OCR** or **Google Document AI** for handwritten forms
3. Let OCR extract text automatically
4. Forms appear in Dashboard with status **"Extracted"**

### Day 2-3: Verify Forms

1. **Open each form** from Dashboard
2. **Review extracted text**
3. **Manually correct all fields** in the verification form
4. **Save & Verify** each form
5. Forms status changes to **"Verified"**

### Day 4: Prepare Training Data

Once you have **50+ verified forms**:

```bash
# Prepare training data from verified forms
python backend/training/prepare_student_forms_training_data.py \
  training_data/student_forms.json \
  --status verified \
  --min-fields 5
```

### Day 5: Train Model

```bash
# Train CRAFT + TR-OCR on your verified forms
python backend/training/train_craft_trocr.py \
  training_data/student_forms.json \
  models/trocr_student_forms \
  --epochs 20 \
  --batch-size 8
```

---

## ✅ Verification Checklist

Before marking a form as verified, ensure:

- [ ] **Student Name** is entered (required field)
- [ ] All dates are in correct format
- [ ] Phone numbers are 10 digits
- [ ] Email addresses are valid format
- [ ] Addresses are complete (street, city, state, pincode)
- [ ] Educational qualifications are accurate
- [ ] Course details are correct
- [ ] All handwritten text is correctly transcribed

---

## 🎯 Tips for Best Results

### 1. Image Quality
- **Use high-resolution scans** (300+ DPI)
- **Ensure good lighting** when scanning
- **Avoid shadows** and reflections
- **Keep forms flat** when scanning

### 2. OCR Provider Selection
- **Handwritten forms**: Use CRAFT + TR-OCR or Google Document AI
- **Printed forms**: Use Tesseract (free) or Google Vision
- **Structured forms**: Use Azure Form Recognizer

### 3. Verification Process
- **Verify immediately** after upload for best accuracy
- **Compare with original** scanned image
- **Double-check numbers** (phone, Aadhar, percentages)
- **Verify dates** are in correct format

### 4. Batch Processing
- Upload multiple forms at once
- Verify them systematically
- Keep track of verified count

---

## 🔧 Troubleshooting

### Problem: Form image not showing

**Solution:**
- Check if file exists in `uploads/` directory
- Refresh the page
- Check browser console for errors

### Problem: OCR extraction failed

**Solution:**
- Try a different OCR provider
- Check image quality (should be clear and readable)
- Ensure file format is supported (PDF, JPG, PNG)

### Problem: Fields not auto-filling

**Solution:**
- Click "Auto-fill Fields" button manually
- Check if raw text contains the information
- Manually enter if auto-fill doesn't work

### Problem: Can't save form

**Solution:**
- Ensure **Student Name** is filled (required)
- Check backend server is running
- Check browser console for errors

---

## 📊 After Verification

Once forms are verified:

1. **Search forms** by name, phone, email, course
2. **Export data** to CSV or JSON
3. **View student profiles** with all forms
4. **Prepare training data** for model training
5. **Train custom model** on your verified forms

---

## 🎓 Next Steps

After verifying 50+ forms:

1. **Prepare training data:**
   ```bash
   python backend/training/prepare_student_forms_training_data.py \
     training_data/student_forms.json \
     --status verified
   ```

2. **Train your model:**
   ```bash
   python backend/training/train_craft_trocr.py \
     training_data/student_forms.json \
     models/trocr_student_forms \
     --epochs 20
   ```

3. **Use trained model:**
   - Set `TROCR_CUSTOM_MODEL_PATH` environment variable
   - Or update provider to use custom model
   - Future forms will have better accuracy!

---

## 📝 Quick Reference

### Start Application
```bash
# Terminal 1: Backend
python -m uvicorn backend.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend && npm run dev
```

### Access Points
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

### Key Actions
- **Upload**: Click "Upload" → Choose file → Select OCR → Upload
- **Verify**: Dashboard → Click "View" → Correct fields → "Save & Verify"
- **Re-extract**: Verification View → Select provider → "Run OCR"

---

**You're ready to start digitizing student forms! 🎉**

For detailed training guide, see [TRAINING_STUDENT_FORMS.md](TRAINING_STUDENT_FORMS.md)

