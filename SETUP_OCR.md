# OCR Setup Guide for Student Records Management System

This guide will help you set up the best OCR providers for handwritten form digitization.

## OCR Provider Recommendations

### For Handwritten Forms (BEST to GOOD):

1. **Google Cloud Document AI** ⭐⭐⭐⭐⭐ (BEST)
   - Specifically designed for handwritten text and forms
   - Excellent accuracy for handwriting recognition
   - Supports form field detection and key-value extraction
   - Cost: Pay-as-you-go (first 1000 pages free per month)

2. **Azure Form Recognizer** ⭐⭐⭐⭐⭐ (BEST)
   - Excellent for structured forms with checkboxes
   - Very good handwriting recognition
   - Detects form fields, tables, and selection marks
   - Cost: Pay-as-you-go (first 500 pages free per month)

3. **AWS Textract** ⭐⭐⭐⭐
   - Good for forms and handwriting
   - Supports form data extraction and tables
   - Cost: Pay-as-you-go (first 1000 pages free per month)

4. **Google Cloud Vision** ⭐⭐⭐⭐
   - Good general OCR with decent handwriting support
   - Easier to set up than Document AI
   - Cost: Pay-as-you-go (first 1000 units free per month)

5. **Tesseract OCR** ⭐⭐⭐ (FREE)
   - Free and open-source
   - Good for printed text, moderate for handwriting
   - No cloud costs
   - **Already configured and working**

6. **Tesseract + Google Vision Combined** ⭐⭐⭐⭐⭐ (BEST for complex layouts)
   - Combines Tesseract's excellent layout detection with Google Vision's superior character recognition
   - Ideal for documents with columns, complex layouts, historical fonts, or diacritics
   - Best of both worlds: accurate layout structure + accurate character recognition
   - Based on Programming Historian methodology
   - Cost: Google Vision pricing applies (first 1000 units free per month)
   - **Requires both Tesseract and Google Vision to be enabled**

---

## Setup Instructions

### Option 1: Google Cloud Document AI (RECOMMENDED for Handwriting)

#### Prerequisites
- Google Cloud account
- Google Cloud Project with billing enabled

#### Steps

1. **Enable the Document AI API**
   ```bash
   # Install gcloud CLI if not already installed
   curl https://sdk.cloud.google.com | bash
   
   # Initialize and login
   gcloud init
   
   # Enable Document AI API
   gcloud services enable documentai.googleapis.com
   ```

2. **Create a Form Parser Processor**
   - Go to [Google Cloud Console > Document AI](https://console.cloud.google.com/ai/document-ai)
   - Click "Create Processor"
   - Select "Form Parser" (best for admission forms)
   - Choose region (e.g., us or eu)
   - Note the Processor ID

3. **Create Service Account**
   ```bash
   # Create service account
   gcloud iam service-accounts create ocr-service-account \
       --description="OCR Service Account" \
       --display-name="OCR Service Account"
   
   # Grant Document AI User role
   gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
       --member="serviceAccount:ocr-service-account@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
       --role="roles/documentai.apiUser"
   
   # Create and download key
   gcloud iam service-accounts keys create ~/ocr-key.json \
       --iam-account=ocr-service-account@YOUR_PROJECT_ID.iam.gserviceaccount.com
   ```

4. **Install Python Dependencies**
   ```bash
   pip install google-cloud-documentai==2.20.0
   ```

5. **Configure Environment Variables**
   
   Create a `.env` file in the project root:
   ```env
   # Google Document AI Configuration
   GOOGLE_DOCUMENT_AI_PROJECT_ID=your-project-id
   GOOGLE_DOCUMENT_AI_LOCATION=us  # or eu, asia
   GOOGLE_DOCUMENT_AI_PROCESSOR_ID=your-processor-id
   GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/ocr-key.json
   
   # Set default OCR provider
   OCR_PROVIDER=google-documentai
   ```

6. **Test the Setup**
   ```bash
   # Start the backend
   python -m uvicorn backend.main:app --reload --port 8000
   
   # In another terminal, check available providers
   curl http://localhost:8000/api/providers
   ```

---

### Option 2: Azure Form Recognizer (RECOMMENDED for Forms)

#### Prerequisites
- Azure account with active subscription

#### Steps

1. **Create Form Recognizer Resource**
   - Go to [Azure Portal](https://portal.azure.com)
   - Create a new resource: "Form Recognizer"
   - Select pricing tier (Free F0 or Standard S0)
   - Note the endpoint and key

2. **Install Python Dependencies**
   ```bash
   pip install azure-ai-formrecognizer==3.3.0
   ```

3. **Configure Environment Variables**
   
   Add to `.env` file:
   ```env
   # Azure Form Recognizer Configuration
   AZURE_FORM_RECOGNIZER_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
   AZURE_FORM_RECOGNIZER_KEY=your-key-here
   
   # Set default OCR provider
   OCR_PROVIDER=azure-form-recognizer
   ```

---

### Option 3: AWS Textract

#### Prerequisites
- AWS account with access to Textract

#### Steps

1. **Create IAM User with Textract Access**
   - Go to AWS IAM Console
   - Create new user with programmatic access
   - Attach policy: `AmazonTextractFullAccess`
   - Note the Access Key ID and Secret Access Key

2. **Install Python Dependencies**
   ```bash
   pip install boto3==1.34.0
   ```

3. **Configure Environment Variables**
   
   Add to `.env` file:
   ```env
   # AWS Textract Configuration
   AWS_ACCESS_KEY_ID=your-access-key-id
   AWS_SECRET_ACCESS_KEY=your-secret-access-key
   AWS_REGION=us-east-1  # or your preferred region
   
   # Set default OCR provider
   OCR_PROVIDER=aws-textract
   ```

---

### Option 4: Google Cloud Vision (Simpler Alternative)

#### Prerequisites
- Google Cloud account

#### Steps

1. **Enable Vision API**
   ```bash
   gcloud services enable vision.googleapis.com
   ```

2. **Use same service account from Document AI** or create a new one with Vision API access

3. **Install Python Dependencies**
   ```bash
   pip install google-cloud-vision==3.7.0
   ```

4. **Configure Environment Variables**
   
   Add to `.env` file:
   ```env
   # Google Cloud Vision Configuration
   GOOGLE_CLOUD_PROJECT_ID=your-project-id
   GOOGLE_CLOUD_API_KEY=your-api-key  # Optional, can use service account
   GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/ocr-key.json
   
   # Set default OCR provider
   OCR_PROVIDER=google-vision
   ```

---

### Option 5: Tesseract + Google Vision Combined (BEST for Complex Layouts)

This provider combines Tesseract's superior layout detection with Google Vision's excellent character recognition, ideal for documents with columns, complex layouts, or challenging fonts (historical fonts, diacritics, ligatures).

Based on the methodology from [Programming Historian: OCR with Google Vision and Tesseract](https://programminghistorian.org/en/lessons/ocr-with-google-vision-and-tesseract).

#### Prerequisites
- Both Tesseract and Google Cloud Vision must be set up (see Options 4 and 5)
- Tesseract must be installed (already included)
- Google Cloud Vision API access

#### Steps

1. **Ensure Tesseract is Installed**
   - Tesseract should already be working (see Option 5 below)
   - Verify: `tesseract --version`

2. **Ensure Google Vision is Configured**
   - Follow Option 4 above to set up Google Cloud Vision
   - Verify credentials are in place

3. **Configure Environment Variables**
   
   Add to `.env` file:
   ```env
   # Enable both providers
   OCR_ENABLE_TESSERACT=true
   OCR_ENABLE_GOOGLE_VISION=true
   OCR_ENABLE_TESSERACT_GOOGLE_COMBINED=true
   
   # Google Cloud Vision Configuration (from Option 4)
   GOOGLE_CLOUD_PROJECT_ID=your-project-id
   GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/ocr-key.json
   
   # Set default OCR provider (optional)
   OCR_PROVIDER=tesseract-google-combined
   # or use alias:
   OCR_PROVIDER=combined
   ```

4. **How It Works**
   - **Tesseract** identifies text regions (layout detection)
   - **Google Vision** recognizes characters within those regions (character recognition)
   - Words from Google Vision are matched to Tesseract regions using coordinate matching
   - Result: Accurate layout structure + accurate character recognition

5. **When to Use This Provider**
   - Documents with multiple columns
   - Forms with complex layouts
   - Historical documents with unusual fonts
   - Documents with diacritics, ligatures, or special characters
   - When layout accuracy AND character accuracy are both important

**Note:** This provider uses Google Vision's `document_text_detection` API, which counts toward your Google Cloud Vision quota.

---

### Option 6: Tesseract OCR (FREE, Already Working)

Tesseract is already installed and configured! To improve accuracy:

1. **Install Language Data**
   ```bash
   # On Ubuntu/Debian
   sudo apt-get install tesseract-ocr-eng tesseract-ocr-hin
   
   # On macOS
   brew install tesseract-lang
   ```

2. **Use Enhanced Preprocessing** (automatically applied)
   The system already applies image enhancement for better OCR results.

---

## Choosing the Best Provider

### For SRCC Admission Forms (Handwritten):
**Recommended:** Google Document AI or Azure Form Recognizer

### For Cost-Conscious Setup:
**Recommended:** Tesseract (free) or use free tiers of cloud providers

### For Highest Accuracy:
**Recommended:** Use multiple providers and compare results

### For Complex Layouts (Columns, Tables, Multi-column Forms):
**Recommended:** Tesseract + Google Vision Combined provider
- Best layout detection (Tesseract) + best character recognition (Google Vision)
- Ideal for historical documents or forms with complex structures

---

## Testing Your Setup

1. **Start the Backend Server**
   ```bash
   python -m uvicorn backend.main:app --reload --port 8000
   ```

2. **Start the Frontend**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

3. **Upload a Test Form**
   - Open http://localhost:5173
   - Click "Upload"
   - Select your scanned admission form
   - Choose your OCR provider
   - Click "Upload Form"

4. **Verify Results**
   - View the extracted text
   - Check the auto-filled form fields
   - Verify and correct any errors
   - Save the verified form

---

## Troubleshooting

### Google Cloud Document AI

**Error: "Permission denied"**
- Ensure service account has `roles/documentai.apiUser` role
- Check that GOOGLE_APPLICATION_CREDENTIALS path is correct

**Error: "Processor not found"**
- Verify processor ID is correct
- Ensure processor is in the same region as specified in GOOGLE_DOCUMENT_AI_LOCATION

### Azure Form Recognizer

**Error: "Invalid endpoint"**
- Ensure endpoint includes `https://` and ends with `/`
- Verify the key is from the same resource as the endpoint

### AWS Textract

**Error: "Access denied"**
- Ensure IAM user has Textract permissions
- Verify AWS credentials are correct in .env file

### Tesseract

**Error: "Tesseract not found"**
```bash
# Install Tesseract
# Ubuntu/Debian:
sudo apt-get install tesseract-ocr

# macOS:
brew install tesseract

# Windows:
# Download installer from https://github.com/UB-Mannheim/tesseract/wiki
```

---

## Cost Comparison

| Provider | Free Tier | Cost After Free Tier | Best For |
|----------|-----------|---------------------|----------|
| Google Document AI | 1000 pages/month | $0.01-0.05/page | Handwriting, Forms |
| Azure Form Recognizer | 500 pages/month | $0.01-0.05/page | Structured Forms |
| AWS Textract | 1000 pages/month | $0.0015-0.05/page | Forms, Tables |
| Google Vision | 1000 units/month | $1.50/1000 units | General OCR |
| Tesseract | Unlimited FREE | FREE | Printed Text |

---

## Recommendations for Production

1. **Start with Free Tier**: Test all providers with your actual forms
2. **Measure Accuracy**: Compare results to see which works best for your forms
3. **Monitor Costs**: Set up billing alerts in cloud consoles
4. **Fallback Strategy**: Configure multiple providers, use Tesseract as fallback
5. **Batch Processing**: Process multiple forms at once to optimize API usage

---

## Next Steps

After setting up OCR:
1. Upload test forms
2. Verify OCR accuracy
3. Train staff on verification interface
4. Set up regular backups
5. Configure user authentication (if needed)

For more information, see the main [README.md](README.md).
