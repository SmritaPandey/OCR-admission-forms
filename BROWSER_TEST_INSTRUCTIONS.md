# Browser Testing Instructions

## System Status ✅

Both servers are running:
- **Backend**: http://localhost:8000 ✅
- **Frontend**: http://localhost:5173 ✅

## Test Real Student Forms

You have **14 real student form PDFs** in `data/samples/pdfs/`:
1. UN-01-243550037803-NAVYA RAJ.pdf
2. UN-02-243550630824-ARYAN.pdf
3. UN-03-243550516046-KARAN YADAV.pdf
4. UN-04-243550774198-DEVESH VERMA.pdf
5. UN-05-243550336680-PESHL KUMAR.pdf
6. UN-250-243551539583-DIYA.pdf
7. UN-251-243550620879-KHUSHI MEENA.pdf
8. jatin.pdf
9. paridhi kiran.pdf
10. ravi chaudhary.pdf
11. sara hanfi.pdf
12. SRCC DATA FORM-1-4.pdf
13. student data form scanned.pdf
14. ujjwal kumar.pdf

## Steps to Test in Browser

### 1. Open the Application

Open your browser and navigate to:
**http://localhost:5173**

### 2. Upload a Form

1. Click **"New Submission"** button in the navigation (or go to `/upload`)
2. Click **"Choose File"** or drag and drop a PDF
3. Select one of the student forms from `data/samples/pdfs/`
4. Select OCR Provider:
   - **Tesseract** (free, already working) ✅
   - **Tesseract + Google Vision Combined** (if Google credentials configured)
5. Click **"Upload Form"**

### 3. View Extraction Results

After upload:
- The system will extract text from the form
- You'll see the extracted raw text
- Form fields will be auto-filled where detected
- Review and verify the extracted data

### 4. Verify and Save

1. Review all extracted fields:
   - Student Name
   - Date of Birth
   - Address
   - Phone Number
   - Email
   - Guardian Information
   - Course Applied
   - Multiple choice questions (checkboxes)
2. Correct any mistakes
3. Click **"Save & Verify"**

### 5. Test Multiple Forms

Upload several forms to:
- Test different handwriting styles
- Test various form layouts
- Build up training data

### 6. Use Auto-Labeling (Training)

After uploading forms:
1. Go to Dashboard
2. Forms will appear in the list
3. Use the API to auto-label them for training:
   ```bash
   curl -X POST "http://localhost:8000/api/auto-label/1?save_annotation=true"
   ```

## Testing Checklist

- [ ] Upload form via browser
- [ ] Verify OCR extraction quality
- [ ] Check field detection accuracy
- [ ] Verify checkbox detection
- [ ] Save and verify form
- [ ] Search for uploaded form
- [ ] Export data (CSV/JSON)
- [ ] Test batch upload (multiple forms)
- [ ] Test auto-labeling API
- [ ] Prepare training data

## API Testing (Alternative)

If browser testing isn't available, test via API:

```bash
# Upload a form
curl -X POST http://localhost:8000/api/upload \
  -F "file=@data/samples/pdfs/UN-01-243550037803-NAVYA RAJ.pdf" \
  -F "ocr_provider=tesseract"

# Auto-label for training
curl -X POST "http://localhost:8000/api/auto-label/1?save_annotation=true"

# Check training stats
curl http://localhost:8000/api/training/stats

# Prepare training data
curl -X POST "http://localhost:8000/api/training/prepare-data?format=both&split=true"
```

## Expected Results

✅ Forms should upload successfully
✅ OCR should extract text from handwritten forms
✅ Fields should be detected and auto-filled
✅ Checkboxes should be detected
✅ Forms should be searchable after verification
✅ Training data can be prepared from uploaded forms

## Troubleshooting

### Forms Not Uploading
- Check file size (should be < 10MB by default)
- Verify file format (PDF, JPG, PNG supported)
- Check server logs for errors

### Poor OCR Quality
- Try different OCR provider
- Use combined Tesseract+Google Vision
- Check image quality (300+ DPI recommended)

### Fields Not Detected
- Review extracted raw text
- Manually fill missing fields
- Improve training data for better detection

## Next Steps After Testing

1. **Upload all 14 forms** to build dataset
2. **Auto-label all forms** using API
3. **Prepare training data** from annotated forms
4. **Train custom OCR model** for your forms
5. **Improve accuracy** with more training data

---

**Ready to test!** Open http://localhost:5173 in your browser and start uploading forms! 🚀
