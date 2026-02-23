# Complete Verification Guide - All Form Fields

## 📋 All 40+ Form Fields You Can Verify

The verification interface includes **ALL** admission form fields organized into 5 sections:

### 1. Basic Details (8 fields)
- ✅ **Student Name** * (Required)
- ✅ Date of Birth
- ✅ Gender (Male/Female/Other dropdown)
- ✅ Category (General/OBC/SC/ST dropdown)
- ✅ Nationality
- ✅ Religion
- ✅ Aadhar Number
- ✅ Blood Group (A+, A-, B+, B-, AB+, AB-, O+, O- dropdown)

### 2. Address Details (5 fields)
- ✅ Permanent Address (textarea)
- ✅ Correspondence Address (textarea)
- ✅ City
- ✅ State
- ✅ Pincode

### 3. Contact Details (5 fields)
- ✅ Phone Number
- ✅ Alternate Phone
- ✅ Email
- ✅ Emergency Contact Name
- ✅ Emergency Contact Phone

### 4. Parent/Guardian Details (10 fields)
- ✅ Father Name
- ✅ Father Occupation
- ✅ Father Phone
- ✅ Mother Name
- ✅ Mother Occupation
- ✅ Mother Phone
- ✅ Guardian Name
- ✅ Guardian Relation
- ✅ Guardian Phone
- ✅ Annual Income

### 5. Educational Qualifications (12 fields)

**10th Standard:**
- ✅ 10th Board
- ✅ 10th Year
- ✅ 10th Percentage
- ✅ 10th School

**12th Standard:**
- ✅ 12th Board
- ✅ 12th Year
- ✅ 12th Percentage
- ✅ 12th School

**Additional:**
- ✅ Previous Qualification
- ✅ Graduation Details (textarea)

### 6. Course Application Details (4 fields)
- ✅ Course Applied
- ✅ Application Number
- ✅ Enrollment Number
- ✅ Admission Date

---

## 🎯 How to Verify Each Field

### Step 1: View the Scanned Form
- The scanned form image is displayed on the **left side**
- You can zoom, scroll, and view all pages
- For PDFs, use page navigation to see all pages

### Step 2: Review Extracted Text
- **Raw OCR text** is shown in the "Extracted Text (Raw)" section
- Check if the text was extracted correctly
- Look for any missing or garbled text

### Step 3: Auto-Fill (Optional)
- Click **"🔄 Auto-fill Fields"** to attempt automatic extraction
- This tries to parse the raw text into fields
- **Always review and correct** auto-filled data

### Step 4: Manual Correction
- **Click on any field** to edit
- **Type or paste** the correct value
- **Use dropdowns** for Gender, Category, Blood Group
- **Use textareas** for addresses and graduation details

### Step 5: Verify Accuracy
- **Compare with scanned form** on the left
- **Double-check numbers** (phone, Aadhar, percentages)
- **Verify dates** are in correct format (DD/MM/YYYY)
- **Check spelling** of names and addresses

### Step 6: Save
- **Scroll to bottom** of the form
- **Click "Save & Verify"** to mark as verified
- Or click **"Update"** to save without verifying

---

## 🔍 Field-by-Field Verification Tips

### Student Name (Required)
- **Must be filled** to save the form
- Check spelling carefully
- Include middle name if present

### Date of Birth
- Format: DD/MM/YYYY or DD-MM-YYYY
- Verify year is correct
- Check month and day

### Phone Numbers
- Should be 10 digits (India)
- Remove spaces and dashes
- Verify country code if present

### Email
- Check for typos
- Verify @ symbol and domain
- Common mistakes: .com vs .co.in

### Addresses
- Include complete address
- Street, area, city, state, pincode
- Verify pincode is 6 digits

### Educational Qualifications
- **10th/12th Board**: CBSE, ICSE, State Board, etc.
- **Year**: Graduation year
- **Percentage**: Verify decimal points
- **School**: Full school name

### Course Details
- **Course Applied**: Full course name
- **Application Number**: Verify format
- **Enrollment Number**: Check for typos
- **Admission Date**: Format: DD/MM/YYYY

---

## ⚡ Quick Actions

### Re-Extract with Better OCR
1. Select **"CRAFT + TR-OCR"** from provider dropdown
2. Click **"Run OCR"**
3. Wait for extraction
4. Review new results

### Reset Changes
- Click **"↩ Reset Changes"** to undo all edits
- Returns to original extracted values

### Update Without Verifying
- Click **"Update"** button (top right)
- Saves changes but keeps status as "Extracted"
- Useful for saving progress

### Delete Form
- Click **"Delete"** button (top right)
- Confirms before deletion
- **Cannot be undone**

---

## 📊 Verification Status

Forms have different statuses:

- **Uploaded**: File uploaded, OCR not run yet
- **Extracting**: OCR in progress
- **Extracted**: OCR complete, needs verification
- **Verified**: All fields verified and saved ✅
- **Error**: OCR failed

**Only "Verified" forms** are used for training data!

---

## ✅ Quality Checklist

Before marking as verified:

- [ ] Student Name is correct and complete
- [ ] All dates are in correct format
- [ ] Phone numbers are 10 digits
- [ ] Email addresses are valid
- [ ] Addresses are complete
- [ ] Educational details match the form
- [ ] Course information is accurate
- [ ] All handwritten text is correctly transcribed
- [ ] No fields are left blank (unless not on form)
- [ ] All information matches the scanned form

---

## 🎓 Best Practices

1. **Verify immediately** after upload for best accuracy
2. **Compare side-by-side** with scanned form
3. **Double-check numbers** - they're easy to misread
4. **Verify dates** - common OCR errors
5. **Check spelling** of names and places
6. **Save progress** regularly with "Update" button
7. **Use "Reset Changes"** if you make mistakes

---

## 🚀 After Verification

Once you have **50+ verified forms**:

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
     models/trocr_student_forms
   ```

3. **Future forms** will have better accuracy!

---

**All 40+ fields are ready for manual correction! 🎉**

See [RUN_AND_VERIFY_FORMS.md](RUN_AND_VERIFY_FORMS.md) for complete workflow.

