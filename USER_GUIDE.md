# User Guide: Student Records Management System

## Table of Contents
1. [System Overview](#system-overview)
2. [Getting Started](#getting-started)
3. [Uploading Forms](#uploading-forms)
4. [Verifying and Editing Records](#verifying-and-editing-records)
5. [Searching Records](#searching-records)
6. [Managing Documents](#managing-documents)
7. [Exporting Data](#exporting-data)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)

---

## System Overview

The Student Records Management System is designed to digitize handwritten admission forms using OCR (Optical Character Recognition) technology. The system automatically extracts text from scanned forms and allows staff to verify and correct the information before saving it to the database.

### Key Features

- **Automatic OCR**: Extracts text from scanned forms automatically
- **Multiple OCR Providers**: Support for Tesseract, Google Cloud, Azure, and AWS OCR
- **Verification Interface**: Side-by-side view of scanned form and extracted data
- **Document Management**: Attach supporting documents (ID proof, certificates, etc.)
- **Powerful Search**: Search by name, enrollment number, phone, email, or status
- **Data Export**: Export records to CSV or JSON format
- **Student Profiles**: Automatic linking of forms and documents to student profiles

---

## Getting Started

### Accessing the System

1. Open your web browser
2. Navigate to: `http://localhost:5173` (or your deployed URL)
3. You'll see the Dashboard with statistics

### Dashboard Overview

The Dashboard shows:
- **Total Forms**: Number of forms uploaded
- **Verified Forms**: Forms that have been reviewed and saved
- **Pending Forms**: Forms waiting for verification
- **Recent Forms**: Latest uploaded forms

---

## Uploading Forms

### Step 1: Navigate to Upload Page

Click **"Upload"** in the navigation menu.

### Step 2: Prepare Your Form

**Best Practices for Scanning:**
- Use 300 DPI or higher resolution
- Ensure good lighting and no shadows
- Keep the form flat (no wrinkles or folds)
- Use portrait orientation
- Save as: PDF, JPG, PNG, TIFF, or BMP

### Step 3: Select OCR Provider

Choose an OCR provider based on your needs:

| Provider | Best For | Accuracy | Cost |
|----------|----------|----------|------|
| **Google Document AI** | Handwritten forms | ⭐⭐⭐⭐⭐ | Paid |
| **Azure Form Recognizer** | Structured forms | ⭐⭐⭐⭐⭐ | Paid |
| **AWS Textract** | Forms & tables | ⭐⭐⭐⭐ | Paid |
| **Google Vision** | General OCR | ⭐⭐⭐⭐ | Paid |
| **Tesseract** | Printed text | ⭐⭐⭐ | Free |

**Recommendation for Handwritten Forms:** Use **Google Document AI** or **Azure Form Recognizer**

### Step 4: Upload the Form

1. Click **"Choose File"** and select your scanned form
2. Select your OCR provider from the dropdown
3. Click **"Upload Form"**
4. Wait for OCR processing (usually 5-30 seconds)

### Step 5: Review the Extraction

After upload, you'll be redirected to the verification page automatically.

---

## Verifying and Editing Records

### The Verification Interface

The verification page has two main sections:

**Left Side: Scanned Form**
- View the original scanned document
- For PDFs: Navigate between pages using arrow buttons
- Use "View All Pages" button to see all pages at once

**Right Side: Extracted Data**
- Raw OCR text with confidence score
- Form fields organized by sections
- Auto-filled with extracted information

### Form Sections

1. **Basic Details**
   - Student Name (required)
   - Date of Birth
   - Gender
   - Category (General/OBC/SC/ST/Other)
   - Nationality
   - Religion
   - Aadhar Number
   - Blood Group

2. **Address Details**
   - Permanent Address
   - Correspondence Address
   - City, State, Pincode

3. **Contact Details**
   - Phone Number
   - Alternate Phone
   - Email
   - Emergency Contact Name & Phone

4. **Parent/Guardian Details**
   - Father's Name, Occupation, Phone
   - Mother's Name, Occupation, Phone
   - Guardian Name, Relation, Phone
   - Annual Income

5. **Educational Qualifications**
   - 10th: Board, Year, Percentage, School
   - 12th: Board, Year, Percentage, School
   - Previous Qualification
   - Graduation Details

6. **Course Application Details**
   - Course Applied
   - Application Number
   - Enrollment Number
   - Admission Date

### Verifying the Data

1. **Review Extracted Text**: Check the raw OCR output and confidence score
2. **Auto-fill Fields**: Click "🔄 Auto-fill Fields" to parse the text into form fields
3. **Manual Corrections**: Edit any incorrect or missing information
4. **Save**: Click "Save & Verify" when all information is correct

**Important:** Student Name is required. All other fields are optional.

### Re-extracting Forms

If OCR results are poor:
1. Click **"Re-extract"** button
2. Select a different OCR provider
3. Click **"Re-extract"** in the dialog
4. Review the new results

---

## Searching Records

### Basic Search

1. Click **"Search"** in the navigation menu
2. Enter search criteria in any field:
   - **Student Name**: Partial match (e.g., "John" finds "John Smith")
   - **Phone Number**: Partial match
   - **Email**: Partial match
   - **Enrollment Number**: Find by enrollment number
   - **Application Number**: Find by application number
   - **Course Applied**: Partial match
   - **Status**: Filter by form status

3. Click **"Search"**

### Advanced Filtering

**Filter by Status:**
- **Uploaded**: Just uploaded, OCR not started
- **Extracting**: OCR in progress
- **Extracted**: OCR complete, awaiting verification
- **Verified**: Data verified and saved
- **Error**: OCR or processing error

**Multiple Criteria:** You can combine multiple search fields for precise results.

### Search Results

Results show:
- Student Name
- Phone Number
- Email
- Course Applied
- Upload Date
- Status badge
- Action buttons (View, Delete)

### Viewing a Record

Click **"View"** on any search result to open the verification page for that form.

### Deleting a Record

1. Click **"Delete"** on the search result
2. Confirm deletion
3. The form and its file will be permanently deleted

---

## Managing Documents

Each student record can have multiple attached documents (ID proof, certificates, medical certificates, etc.).

### Uploading Documents

1. Open a form in verification view
2. Scroll down to **"Attached Documents"** section
3. Click **"Choose File"** under "Upload New Document"
4. Select document category:
   - ID Proof (Aadhar, Passport, etc.)
   - Academic Certificate (10th, 12th, Degree)
   - Medical Certificate
   - Birth Certificate
   - Income Certificate
   - Caste Certificate
   - Other

5. Add optional description
6. Click **"Upload Document"**

### Viewing Documents

Uploaded documents appear in the list with:
- Document name
- Category badge
- Upload date
- File size
- Action buttons

### Downloading Documents

Click the **"View"** button next to any document to download it.

### Deleting Documents

1. Click **"Delete"** button next to the document
2. Confirm deletion
3. Document will be permanently removed

---

## Exporting Data

### Export All Records

1. Go to **Dashboard** or **Search** page
2. Click **"Export CSV"** or **"Export JSON"**
3. The file will be downloaded automatically

### Export Formats

**CSV Format:**
- Opens in Excel, Google Sheets
- Good for data analysis and reports
- One row per student

**JSON Format:**
- Machine-readable format
- Good for data integration
- Includes all fields and metadata

### Filtered Export

To export only specific records:
1. Go to **Search** page
2. Enter your search criteria
3. Click **"Search"**
4. Click **"Export CSV"** or **"Export JSON"**
5. Only filtered results will be exported

---

## Best Practices

### Scanning Forms

✅ **DO:**
- Scan at 300 DPI or higher
- Ensure good lighting
- Keep forms flat and straight
- Use color or grayscale mode
- Check scan quality before uploading

❌ **DON'T:**
- Use low resolution (below 150 DPI)
- Scan in poor lighting
- Include shadows or reflections
- Crop important information
- Use heavily compressed images

### OCR Provider Selection

**For Handwritten Forms:**
1st choice: Google Document AI
2nd choice: Azure Form Recognizer
3rd choice: AWS Textract

**For Printed Forms:**
1st choice: Any cloud provider
2nd choice: Tesseract (free)

**For Mixed Forms:**
Use cloud providers for best results

### Data Verification

✅ **Always Verify:**
- Student name (most important)
- Contact information
- Educational qualifications
- Dates and numbers

✅ **Double-check:**
- Aadhar numbers (12 digits)
- Pincodes (6 digits)
- Email addresses
- Phone numbers (10 digits)

### Document Management

✅ **Best Practices:**
- Upload all required documents immediately
- Use correct document categories
- Add descriptive notes when needed
- Keep original files as backup
- Verify file quality before upload

---

## Troubleshooting

### OCR Issues

**Problem: Low confidence score (<70%)**
- **Solution**: Re-scan at higher resolution or re-extract with different provider

**Problem: Missing or incorrect text**
- **Solution**: Manually correct the fields or re-extract with better OCR provider

**Problem: OCR fails completely**
- **Solution**: 
  1. Check file format (should be PDF, JPG, PNG, TIFF, or BMP)
  2. Verify file is not corrupted
  3. Try different OCR provider
  4. If using cloud providers, check your API credentials

### Upload Issues

**Problem: File upload fails**
- **Solution**: 
  1. Check file size (max 10MB)
  2. Verify file format is supported
  3. Check internet connection
  4. Try refreshing the page

**Problem: Upload is very slow**
- **Solution**:
  1. Reduce file size (compress image)
  2. Check internet speed
  3. Use cloud OCR providers during off-peak hours

### Search Issues

**Problem: No results found**
- **Solution**:
  1. Try partial name (e.g., first name only)
  2. Remove extra spaces
  3. Check spelling
  4. Try different search fields
  5. Verify the record was actually saved (check status)

**Problem: Too many results**
- **Solution**: Add more search criteria to narrow results

### Document Issues

**Problem: Can't view/download document**
- **Solution**:
  1. Check if file still exists on server
  2. Try refreshing the page
  3. Check browser console for errors
  4. Contact administrator

**Problem: Document upload fails**
- **Solution**:
  1. Check file size (max 10MB)
  2. Verify file format
  3. Check available disk space on server
  4. Try uploading a smaller file

### General Issues

**Problem: Page not loading**
- **Solution**:
  1. Check internet connection
  2. Refresh the page (F5 or Ctrl+R)
  3. Clear browser cache
  4. Try different browser
  5. Check if backend server is running

**Problem: Changes not saving**
- **Solution**:
  1. Ensure Student Name is filled (required field)
  2. Check for error messages
  3. Verify internet connection
  4. Try again after refreshing

---

## Keyboard Shortcuts

- **Tab**: Move to next field
- **Shift+Tab**: Move to previous field
- **Ctrl+S**: Save form (when in verification view)
- **Esc**: Close dialogs

---

## Tips for Efficient Workflow

1. **Batch Processing**: Upload multiple forms at once, then verify them sequentially
2. **Use Auto-fill**: Always click "Auto-fill Fields" first before manual editing
3. **Tab Navigation**: Use Tab key to move quickly between fields
4. **Regular Saves**: Save your work frequently (use Update button)
5. **Document Upload**: Upload all documents immediately after verifying the form
6. **Quality Check**: Set aside 5-10% of records for random quality checks
7. **Backup**: Regularly export data as backup

---

## System Administration

### For Administrators

**User Management:**
- Currently, the system has no authentication
- For production: Implement user authentication and role-based access

**Database Maintenance:**
- Regular backups recommended (daily or weekly)
- Database file: `admission_forms.db` (SQLite) or PostgreSQL database

**File Storage:**
- Uploaded files stored in `uploads/` directory
- Monitor disk space regularly
- Implement file cleanup policies for old records

**OCR Configuration:**
- Set up API credentials in `.env` file
- Monitor API usage and costs
- Set up billing alerts in cloud provider dashboards

---

## Getting Help

### Documentation
- **README.md**: Installation and setup guide
- **SETUP_OCR.md**: OCR provider configuration
- **SYSTEM_OVERVIEW.md**: Technical architecture
- **API Documentation**: http://localhost:8000/docs (when backend is running)

### Support
For technical issues or questions:
1. Check this user guide
2. Review error messages in browser console (F12)
3. Check backend logs
4. Contact your system administrator

---

## Appendix: Field Descriptions

| Field | Description | Format | Required |
|-------|-------------|--------|----------|
| Student Name | Full name of the student | Text | Yes |
| Date of Birth | Birth date | DD/MM/YYYY | No |
| Gender | Gender | Male/Female/Other | No |
| Category | Social category | General/OBC/SC/ST/Other | No |
| Aadhar Number | 12-digit Aadhar number | 12 digits | No |
| Phone Number | Primary contact | 10 digits | No |
| Email | Email address | Valid email | No |
| Enrollment Number | University enrollment number | Alphanumeric | No |
| Application Number | Application form number | Alphanumeric | No |
| Course Applied | Name of course/program | Text | No |

All fields except "Student Name" are optional.

---

## Version Information

**System Version:** 1.0.0
**Last Updated:** November 2025
**Supported Browsers:** Chrome, Firefox, Safari, Edge (latest versions)

---

For the most up-to-date information, please refer to the online documentation or contact your system administrator.
