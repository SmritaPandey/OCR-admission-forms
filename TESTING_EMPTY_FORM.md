# Testing Empty Form - Status

## Current Status

✅ **Database Schema Fixed**
- Added missing `enrollment_number` column to database
- Database is now compatible with merged code

❌ **Tesseract OCR Not Installed**
- Tesseract is required for local OCR processing
- Currently unavailable, causing upload failures

## Empty Form Test File

**File**: `data/samples/pdfs/student data form scanned.pdf`
- Size: 1.6 MB
- Type: Empty form template (no student data filled in)
- Purpose: Test OCR extraction of form structure and labels

## Expected Behavior

When processing an empty form, the OCR should:
1. ✅ Extract form labels and structure (headers, field names, instructions)
2. ✅ Extract checkbox options and table headers
3. ⚠️ Extract minimal/no student data (since form is empty)
4. ✅ Identify form type and structure

## Installation Options

### Option 1: Install Tesseract (Recommended for Local Testing)

**macOS:**
```bash
# Install Homebrew first (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Tesseract
brew install tesseract

# Verify installation
tesseract --version
```

**Alternative (without Homebrew):**
- Download from: https://github.com/tesseract-ocr/tesseract
- Or use MacPorts: `sudo port install tesseract`

### Option 2: Use AI OCR Providers

If you have API keys configured, you can use:
- **GPT-4 Vision** - Add `OPENAI_API_KEY` to `.env`
- **Claude Vision** - Add `ANTHROPIC_API_KEY` to `.env`
- **Ollama** - Install and run Ollama locally

## Testing Steps

Once Tesseract is installed:

1. **Upload via API:**
```bash
curl -X POST "http://127.0.0.1:8000/api/upload" \
  -F "file=@data/samples/pdfs/student data form scanned.pdf" \
  -F "ocr_provider=tesseract"
```

2. **Upload via Frontend:**
- Navigate to http://localhost:5173/upload
- Select the empty form PDF
- Choose OCR provider
- Upload and view results

3. **Expected Results:**
- Form structure extracted (headers, labels)
- Field names identified
- Checkbox options detected
- No student data (form is empty)
- Form type: "STUDENT'S DATA FORM" from Shri Ram College of Commerce

## Form Structure (Expected Extraction)

Based on the form template, OCR should extract:

### Headers:
- "SHRI RAM COLLEGE OF COMMERCE"
- "STUDENT'S DATA FORM"
- "ACADEMIC SESSION"
- "DOCUMENTS REQUIRED"
- "DECLARATION & UNDERTAKING"

### Field Labels:
- Course selection options
- Admission Category options
- DU Portal Form Number
- CUET Score
- Name fields
- Gender options
- Date of Birth
- Address fields
- Contact information
- Academic details
- Parent/Guardian information

### Tables:
- CUET Score table
- Documents checklist table

## Next Steps

1. **Install Tesseract** (see instructions above)
2. **Restart backend server** if needed
3. **Test empty form upload**
4. **Compare with filled form** (`SRCC DATA FORM-1-4.pdf`) to see difference

## Notes

- Empty forms are useful for:
  - Testing form structure recognition
  - Training data collection
  - Validating OCR accuracy on form labels
  - Testing checkbox detection on empty checkboxes

- The system should handle empty forms gracefully:
  - Extract structure even without data
  - Mark fields as empty/null
  - Still identify form type correctly


