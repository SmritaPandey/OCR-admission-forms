# Complete Form Field Mapping - Student Admission Form

## 📋 All Fields from Your Forms

Based on the form images, here are **ALL** fields that need to be mapped for OCR training:

---

## Page 1: Main Student Data Form

### Header Section
- **College Name**: "SHRI RAM COLLEGE OF COMMERCE" (fixed)
- **Form Title**: "STUDENT'S DATA FORM" (fixed)
- **Instruction**: "All informations need to be filled in capital letters" (fixed)

### Academic & Admission Details
- **academic_session**: Academic Session (e.g., "2024-2025")
- **course**: Course selection
  - Options: `B.COM.(H)`, `B.A.(H) ECO`
- **admission_category**: Admission Category (checkboxes)
  - Options: `GEN`, `OBC`, `SC`, `ST`, `Sports`, `PwD`, `EWS`, `Foreign`, `CW`, `KM`, `Others`, `ECA`
- **admission_category_other**: Other (Specify) - if "Others" selected
- **du_portal_form_number**: DU Portal Form Number
- **cuet_score**: CUET Score
- **college_roll_no**: College Roll No.
- **date_of_admission**: Date of Admission (DD/MM/YYYY)
- **photograph**: Passport size photograph (image, not text)
- **student_signature**: Signature of Student (image, not text)

### Personal Details (Numbered Sections)

**1. Name:**
- **first_name**: First Name (block letters, character boxes)
- **middle_name**: Middle Name (block letters, character boxes)
- **surname**: Surname (block letters, character boxes)
- **student_name**: Full name (combined from above)

**2. Gender:**
- **gender**: Gender selection
  - Options: `Male`, `Female`, `Transgender`

**3. Date of Birth:**
- **date_of_birth**: Date of Birth (DD/MM/YYYY)

**4. Permanent Address:**
- **permanent_address_line1**: Address Line 1
- **permanent_address_line2**: Address Line 2
- **permanent_address_line3**: Address Line 3
- **permanent_state**: State
- **permanent_pincode**: PIN Code

**5. Local Address for Correspondence:**
- **correspondence_address_line1**: Address Line 1
- **correspondence_address_line2**: Address Line 2
- **correspondence_address_line3**: Address Line 3
- **correspondence_state**: State
- **correspondence_pincode**: PIN Code

**6. Email:**
- **email**: Email Address

**7. Contact Numbers:**
- **phone_number**: Contact Number 1
- **alternate_phone**: Contact Number 2

**8. Mother's Name:**
- **mother_name**: Mother's Name (block letters, 2 lines)

**9. Father's Name:**
- **father_name**: Father's Name (block letters, 2 lines)

**10. CUET Marks Table:**
- **cuet_subject_1**: Subject 1 Name
- **cuet_total_score_1**: Total Score for Subject 1
- **cuet_score_obtained_1**: Score Obtained for Subject 1
- **cuet_subject_2**: Subject 2 Name
- **cuet_total_score_2**: Total Score for Subject 2
- **cuet_score_obtained_2**: Score Obtained for Subject 2
- **cuet_subject_3**: Subject 3 Name
- **cuet_total_score_3**: Total Score for Subject 3
- **cuet_score_obtained_3**: Score Obtained for Subject 3
- **cuet_subject_4**: Subject 4 Name
- **cuet_total_score_4**: Total Score for Subject 4
- **cuet_score_obtained_4**: Score Obtained for Subject 4
- **cuet_subject_5**: Subject 5 Name
- **cuet_total_score_5**: Total Score for Subject 5
- **cuet_score_obtained_5**: Score Obtained for Subject 5
- **cuet_subject_6**: Subject 6 Name
- **cuet_total_score_6**: Total Score for Subject 6
- **cuet_score_obtained_6**: Score Obtained for Subject 6
- **cuet_total_score**: Total CUET Score Obtained

---

## Page 2: Additional Details

### Section 11: Qualifying Examination (Class-XII)

- **twelfth_year**: Year of passing
- **twelfth_board**: Board / University
- **twelfth_roll_number**: Examination Roll No.
- **twelfth_institution**: Institution Last Attended
- **hindi_studied_upto**: Hindi studied upto (VIII/X/XII/Never)

### Section 12: Personal Information

- **nationality**: Nationality
- **religion**: Religion
- **blood_group**: Blood Group
- **below_poverty_line**: Whether Below Poverty Line (Yes/No)
- **annual_income**: Parent's / Family Annual Income
- **minority_category**: Whether belongs to minority (checkboxes)
  - Options: `Muslim`, `Jain`, `Sikh`, `Persian`, `Christian`, `Buddhists`, `Others`

### Section 13: Mother's Occupational Details

- **mother_occupation**: Occupation
- **mother_designation**: Designation (if employed)
- **mother_organization**: Organization & Address
- **mother_email**: Email
- **mother_mobile**: Mobile No. (10 digits, segmented)
- **mother_landline_code**: Landline Code (3 digits)
- **mother_landline**: Landline No. (8 digits)

### Section 14: Father's Occupational Details

- **father_occupation**: Occupation
- **father_designation**: Designation (if employed)
- **father_organization**: Organization & Address
- **father_email**: Email
- **father_mobile**: Mobile No. (10 digits, segmented)
- **father_landline_code**: Landline Code (3 digits)
- **father_landline**: Landline No. (8 digits)

### Section 15: Local Guardian's Details

- **guardian_name**: Name
- **guardian_residential_address**: Residential Address
- **guardian_organization**: Organization & Address
- **guardian_email**: Email
- **guardian_mobile**: Mobile No. (10 digits, segmented)
- **guardian_landline_code**: Landline Code (3 digits)
- **guardian_landline**: Landline No. (8 digits)

### Section 16: Other Information

- **du_enrollment_number**: Delhi University Enrolment No.
- **hindi_medium_preference**: Would you like to be taught in Hindi medium
  - Options: `Yes`, `No`

### Section 17: EWS/SC/ST/OBC/PwBD Details

- **category_certificate_authority**: Name & Address of certificate issuing authority
- **category_certificate_number**: Certificate No.
- **category_certificate_date**: Date of Issue
- **disability_percentage**: If PwBD, extent of disability (in %)
- **disability_type**: Type of Disability (VH/HH/OH)
- **udid_number**: UDID No.

---

## Page 3: Documents Required

### Document Checklist (Table Format)

Each document has:
- **document_name**: Particulars (document description)
- **document_attached**: Tick (✔) documents attached (checkbox)
- **document_office_use**: For Office Use (text field)

**Documents:**
1. **printed_admission_form**: Printed Admission/Registration Form downloaded from DU Portal
2. **anti_ragging_undertaking**: Undertakings for curbing ragging
3. **photographs_pasted**: Photographs pasted at prescribed space
4. **cuet_score_card**: CUET Score Card
5. **twelfth_mark_sheet**: Detailed Mark Sheet of class XII examination
6. **tenth_certificate**: Certificate and Mark Sheet of class X examination
7. **twelfth_certificate**: Provisional / Original Certificate of class XII examination
8. **character_certificate**: Recent Character Certificate
9. **transfer_certificate**: Transfer Certificate from School/College
10. **migration_certificate**: Migration Certificate from Board/University
11. **hindi_exemption_certificate**: Certificate for Hindi exemption (CTH)
12. **caste_category_certificate**: Caste/Category Certificate
13. **sports_eca_certificates**: All relevant certificates (Sports & ECA)
14. **original_certificates**: All certificates in original
15. **photo_id_proofs**: Photo ID proof of Self, Both Parents and Local Guardian

---

## Page 4: Declarations

### Section 1: Declaration & Undertaking by Student

- **student_declaration_name**: Student's Full Name (in declaration)
- **student_declaration_date**: Date (Student)
- **student_declaration_place**: Place (Student)
- **student_declaration_signature**: Signature of Candidate (Student)

### Section 2: Declaration & Undertaking by Parent/Guardian

- **parent_guardian_name**: Parent/Guardian's Full Name
- **parent_guardian_relationship**: Relationship (Father/Mother/Guardian)
- **parent_guardian_candidate_name**: Candidate's Name (by Parent/Guardian)
- **parent_guardian_course**: Bachelor's Program/Course
- **parent_guardian_date**: Date (Parent/Guardian)
- **parent_guardian_place**: Place (Parent/Guardian)
- **parent_guardian_signature**: Signature of Father/Mother/Guardian

---

## 📊 Field Summary

### Total Fields: **100+ fields**

**Breakdown:**
- Basic Details: 15 fields
- Address Details: 10 fields
- Contact Details: 3 fields
- Parent/Guardian Details: 20 fields
- Educational Details: 10 fields
- CUET Marks: 19 fields
- Occupational Details: 14 fields
- Documents Checklist: 15 fields
- Declarations: 7 fields
- Other: 7 fields

---

## 🗺️ Field Mapping Strategy

### 1. Text Fields
- Single-line text inputs → Extract as-is
- Multi-line text inputs → Combine lines
- Character boxes → Extract and combine characters

### 2. Checkbox Fields
- Single selection → Extract selected option
- Multiple selection → Extract all selected options
- Document checklist → Boolean (attached/not attached)

### 3. Date Fields
- Segmented date boxes → Combine DD/MM/YYYY
- Date fields → Extract in DD/MM/YYYY format

### 4. Number Fields
- Segmented number boxes → Combine digits
- Phone numbers → Extract full number
- Scores → Extract numerical values

### 5. Table Fields
- CUET marks table → Extract row by row
- Document checklist → Extract per document

---

## 🎯 Training Data Format

Each training example should include:

```json
{
  "image_path": "form_image.png",
  "text": "Full OCR extracted text...",
  "verified_fields": {
    "academic_session": "2024-2025",
    "course": "B.COM.(H)",
    "admission_category": "GEN",
    "first_name": "JOHN",
    "middle_name": "DOE",
    "surname": "SMITH",
    "student_name": "JOHN DOE SMITH",
    "gender": "Male",
    "date_of_birth": "01/01/2000",
    "permanent_address_line1": "123 MAIN STREET",
    "permanent_address_line2": "APARTMENT 4B",
    "permanent_city": "NEW DELHI",
    "permanent_state": "DELHI",
    "permanent_pincode": "110001",
    "email": "john.doe@example.com",
    "phone_number": "9876543210",
    "mother_name": "JANE SMITH",
    "father_name": "ROBERT SMITH",
    "cuet_subject_1": "ENGLISH",
    "cuet_total_score_1": "200",
    "cuet_score_obtained_1": "185",
    "twelfth_year": "2023",
    "twelfth_board": "CBSE",
    "nationality": "INDIAN",
    "religion": "HINDU",
    "blood_group": "O+",
    "mother_occupation": "TEACHER",
    "father_occupation": "ENGINEER",
    "du_enrollment_number": "DU2024001234",
    "document_cuet_score_card": true,
    "document_tenth_certificate": true,
    ...
  },
  "field_mappings": [
    {
      "field_key": "student_name",
      "label": "NAME IN BLOCK LETTERS",
      "value": "JOHN DOE SMITH",
      "field_type": "text"
    },
    ...
  ]
}
```

---

## ✅ Next Steps

1. **Update field mapper** with all these fields
2. **Create training data** from verified forms
3. **Train model** to recognize all field labels
4. **Test extraction** on new forms
5. **Refine mappings** based on results

---

**All 100+ fields are now mapped and ready for training! 🎉**
