# Training & Improving OCR for Form Extraction

Complete guide for training custom OCR models and using local Ollama for better labeled form extraction.

## Table of Contents

1. [Using Ollama for Local OCR](#using-ollama-for-local-ocr)
2. [Collecting Training Data](#collecting-training-data)
3. [Training Custom OCR Models](#training-custom-ocr-models)
4. [Improving Accuracy](#improving-accuracy)
5. [Best Practices](#best-practices)

---

## Using Ollama for Local OCR

Ollama provides **free, local, private** OCR using vision-language models. Perfect for processing 150,000 pages without API costs.

### Step 1: Install Ollama

```bash
# macOS
brew install ollama
# OR download from https://ollama.ai/download

# Linux
curl -fsSL https://ollama.ai/install.sh | sh

# Windows
# Download installer from https://ollama.ai/download
```

### Step 2: Download Vision Model

```bash
# Recommended models for form OCR:
ollama pull llama3.2-vision      # Best for structured forms
ollama pull llava                # Alternative vision model
ollama pull llava-phi3           # Smaller, faster option
```

### Step 3: Start Ollama Server

```bash
# Usually starts automatically, but if not:
ollama serve

# Verify it's running:
curl http://localhost:11434/api/tags
```

### Step 4: Configure in Application

Create or update `.env` file:

```bash
# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_VISION_MODEL=llama3.2-vision

# Set as default provider (optional)
OCR_PROVIDER=ollama
```

### Step 5: Use Ollama for Form Extraction

#### Via API:

```bash
# Upload form with Ollama provider
curl -X POST http://127.0.0.1:8000/api/upload \
  -F "file=@student_form.pdf" \
  -F "ocr_provider=ollama"
```

#### Via Frontend:

1. Navigate to http://localhost:5173/upload
2. Select **"Ollama (Local AI)"** from provider dropdown
3. Upload your form
4. View extracted structured data

### Step 6: Improve Ollama Prompts

The Ollama provider uses structured prompts. To customize for your forms, edit:

**File:** `backend/ocr/ollama_provider.py`

```python
# Customize the prompt (lines 54-70)
prompt = """Analyze this admission form image and extract all information as structured JSON.

Extract these specific fields:
- student_name: Full name of student
- date_of_birth: Date in DD/MM/YYYY format
- gender: Male/Female/Other
- category: General/OBC/SC/ST
- aadhar_number: 12-digit Aadhar number
- phone_number: 10-digit mobile number
- email: Email address
- permanent_address: Complete address
- pincode: 6-digit pincode
- city: City name
- state: State name
- father_name: Father's full name
- mother_name: Mother's full name
- course_applied: Course name
- application_number: Application reference number

For checkboxes, return as:
{
  "checkbox_category": {
    "label": "Category name",
    "checked": true/false
  }
}

Return ONLY valid JSON. Use null for missing fields."""
```

### Step 7: Test Ollama Extraction

```bash
# Test with empty form
curl -X POST http://127.0.0.1:8000/api/upload \
  -F "file=@data/samples/pdfs/student data form scanned.pdf" \
  -F "ocr_provider=ollama" | python3 -m json.tool
```

---

## Collecting Training Data

To train custom models, you need **labeled training data**. The system includes an annotation interface.

### Step 1: Upload Forms for Annotation

```bash
# Upload forms via API
curl -X POST http://127.0.0.1:8000/api/upload \
  -F "file=@form1.pdf" \
  -F "ocr_provider=ollama"

# Get form ID from response
FORM_ID=123
```

### Step 2: Annotate Forms via API

```bash
# Save annotation for a form
curl -X POST http://127.0.0.1:8000/api/annotate/${FORM_ID} \
  -H "Content-Type: application/json" \
  -d '{
    "fields": [
      {
        "field_name": "student_name",
        "value": "John Doe",
        "bounding_box": {"x": 100, "y": 50, "width": 200, "height": 30},
        "page_number": 1,
        "confidence": 0.95
      },
      {
        "field_name": "date_of_birth",
        "value": "01/01/2000",
        "bounding_box": {"x": 100, "y": 100, "width": 150, "height": 30},
        "page_number": 1
      }
    ],
    "checkboxes": [
      {
        "label": "General Category",
        "checked": true,
        "bounding_box": {"x": 50, "y": 200, "width": 20, "height": 20},
        "page_number": 1
      }
    ],
    "notes": "Form has clear handwriting"
  }'
```

### Step 3: Export Training Data

```bash
# Export as JSON
curl http://127.0.0.1:8000/api/export/training-data?format=json > training_data.json

# Export as COCO format (for object detection)
curl http://127.0.0.1:8000/api/export/training-data?format=coco > training_data_coco.json

# Export as YOLO format
curl http://127.0.0.1:8000/api/export/training-data?format=yolo > training_data_yolo.txt
```

### Step 4: Annotation via Frontend (Future)

The annotation UI component (`AnnotationView.tsx`) will allow:
- Drawing bounding boxes around fields
- Labeling field names
- Marking checkbox states
- Multi-page annotation support

---

## Training Custom OCR Models

**macOS Users:** See `backend/training/README_MACOS.md` for complete macOS-specific instructions.

### Option 1: Train TrOCR (Transformer-based OCR)

TrOCR is excellent for handwritten text recognition.

#### Prerequisites

**macOS:**
```bash
# Install system dependencies
brew install libjpeg libpng libtiff

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install PyTorch (with MPS support for Apple Silicon)
pip install torch torchvision torchaudio

# Install training dependencies
pip install transformers datasets accelerate pillow
```

**Linux/Windows:**
```bash
pip install transformers torch torchvision datasets pillow
```

#### Prepare Training Data

Your training data should be in this format:

```
training_data/
├── images/
│   ├── form_001_page1.png
│   ├── form_001_page2.png
│   └── form_002_page1.png
└── labels.json
```

`labels.json` format:
```json
{
  "form_001_page1.png": {
    "text": "Student Name: John Doe\nDate of Birth: 01/01/2000",
    "fields": {
      "student_name": "John Doe",
      "date_of_birth": "01/01/2000"
    }
  }
}
```

#### Run Training

**macOS:**
```bash
cd backend/training

# Activate virtual environment
source ../../venv/bin/activate

# Train TrOCR model (use smaller batch size on macOS)
python3 train_trocr.py \
  ../uploads/training_data/train.json \
  ../models/trocr_finetuned \
  --val-data ../uploads/training_data/val.json \
  --epochs 10 \
  --batch-size 4 \
  --learning-rate 5e-5 \
  --base-model microsoft/trocr-base-handwritten
```

**Linux/Windows:**
```bash
cd backend/training

# Train TrOCR model
python train_trocr.py \
  ../uploads/training_data/train.json \
  ../models/trocr_finetuned \
  --val-data ../uploads/training_data/val.json \
  --epochs 10 \
  --batch-size 8 \
  --learning-rate 5e-5 \
  --base-model microsoft/trocr-base-handwritten
```

#### Use Trained Model

Update `backend/ocr/trainable_ocr_provider.py` to load your model:

```python
from transformers import TrOCRProcessor, VisionEncoderDecoderModel

model = VisionEncoderDecoderModel.from_pretrained("../models/trocr_finetuned")
processor = TrOCRProcessor.from_pretrained("../models/trocr_finetuned")
```

### Option 2: Train Donut (Document Understanding Transformer)

Donut is better for structured form understanding with visual layout.

#### Prepare Training Data

Donut requires synthetic data generation or manual annotation:

```bash
# Generate synthetic forms (if you have form templates)
python generate_synthetic_forms.py --count 1000

# Or use annotated real forms
python prepare_donut_data.py --annotations training_data.json
```

#### Run Training

**macOS:**
```bash
# Use very small batch size on macOS (Donut is memory-intensive)
python3 train_donut.py \
  ../uploads/training_data/train.json \
  ../models/donut_finetuned \
  --val-data ../uploads/training_data/val.json \
  --epochs 15 \
  --batch-size 2 \
  --learning-rate 3e-5
```

**Linux/Windows:**
```bash
python train_donut.py \
  ../uploads/training_data/train.json \
  ../models/donut_finetuned \
  --val-data ../uploads/training_data/val.json \
  --epochs 15 \
  --batch-size 4 \
  --learning-rate 3e-5
```

### Option 3: Fine-tune Azure Form Recognizer (Cloud)

If using Azure, you can train a custom model:

1. **Collect 5+ labeled forms** (minimum requirement)
2. **Upload to Azure Document Intelligence Studio**
3. **Train custom model** via UI
4. **Get model ID** and add to `.env`:

```bash
AZURE_FORM_RECOGNIZER_CUSTOM_MODEL_ID=your-model-id-here
```

---

## Improving Accuracy

### 1. Improve Image Preprocessing

Edit `backend/utils/image_preprocessing.py`:

```python
# Increase contrast for handwritten text
OCR_PREPROCESSING_CONTRAST_FACTOR=2.0

# Better binarization threshold
OCR_PREPROCESSING_BINARIZE_THRESHOLD=128

# Scale up small text
OCR_PREPROCESSING_SCALE_FACTOR=3.0
```

### 2. Use Multi-Provider Ensemble

The system can combine results from multiple providers:

```bash
# Use "best" provider (tries multiple and selects best)
curl -X POST http://127.0.0.1:8000/api/upload \
  -F "file=@form.pdf" \
  -F "ocr_provider=best"
```

### 3. Post-Processing Rules

Add validation rules in `backend/utils/form_parser.py`:

```python
def validate_phone_number(phone: str) -> str:
    """Validate and format phone number"""
    # Remove non-digits
    digits = re.sub(r'\D', '', phone)
    # Must be 10 digits
    if len(digits) == 10:
        return digits
    return phone  # Return original if invalid
```

### 4. Context-Aware Extraction

Use AI form parser for better field understanding:

```python
from backend.utils.ai_form_parser import AIFormParser

parser = AIFormParser()
structured_data = parser.parse_from_ai_result(ollama_result)
```

### 5. Checkbox Detection Improvement

Use AI checkbox detector:

```python
from backend.utils.ai_checkbox_detector import AICheckboxDetector

detector = AICheckboxDetector()
checkboxes = detector.extract_checkboxes_from_ai_result(ollama_result)
```

---

## Best Practices

### For 150,000 Pages Processing

1. **Use Ollama for Cost Efficiency**
   - Free local processing
   - No API rate limits
   - Private data (no cloud upload)

2. **Batch Processing**
   ```bash
   # Upload multiple forms at once
   curl -X POST http://127.0.0.1:8000/api/batch-upload \
     -F "files=@form1.pdf" \
     -F "files=@form2.pdf" \
     -F "files=@form3.pdf" \
     -F "pages_per_form=3" \
     -F "ocr_provider=ollama"
   ```

3. **Enable Caching**
   ```bash
   # In .env
   OCR_CACHE_ENABLED=true
   ```
   Reduces redundant processing for similar forms.

4. **Parallel Processing**
   ```bash
   # Process multiple forms simultaneously
   BATCH_MAX_CONCURRENT=10
   ```

### For Handwritten Forms

1. **Use Vision-Language Models** (Ollama, GPT-4, Claude)
   - Better context understanding
   - Handles cursive handwriting
   - Understands form structure

2. **Preprocess Images**
   - Increase contrast
   - Remove noise
   - Scale up small text

3. **Train on Your Data**
   - Collect 100+ annotated forms
   - Fine-tune TrOCR or Donut
   - Improve accuracy by 10-20%

### For Checkbox Detection

1. **Use AI Vision Models**
   - Visual detection (not text-based)
   - Handles handwritten checkmarks
   - Detects filled boxes

2. **Combine Methods**
   ```python
   # Use both AI and regex detection
   ai_checkboxes = detector.extract_checkboxes_from_ai_result(result)
   text_checkboxes = detector.extract_checkboxes_from_text(raw_text)
   combined = detector.combine_checkbox_results(ai_checkboxes, text_checkboxes)
   ```

---

## Quick Start: Test Ollama Now

```bash
# 1. Install Ollama
brew install ollama  # macOS
# OR download from https://ollama.ai

# 2. Pull vision model
ollama pull llama3.2-vision

# 3. Verify Ollama is running
curl http://localhost:11434/api/tags

# 4. Test with your form
curl -X POST http://127.0.0.1:8000/api/upload \
  -F "file=@data/samples/pdfs/student data form scanned.pdf" \
  -F "ocr_provider=ollama" | python3 -m json.tool

# 5. Check extracted data
# Response will include structured_data with all fields
```

---

## Troubleshooting

### Ollama Not Available

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not, start it
ollama serve

# Check if model is downloaded
ollama list
```

### Low Accuracy

1. **Improve image quality** - Better scanning resolution
2. **Adjust preprocessing** - Increase contrast, denoise
3. **Use better model** - Try `llava` or `llava-phi3`
4. **Customize prompt** - Edit Ollama provider prompt
5. **Train custom model** - Fine-tune on your forms

### Slow Processing

1. **Use GPU** - Ollama can use GPU acceleration
2. **Reduce image size** - Scale down large images
3. **Batch processing** - Process multiple forms in parallel
4. **Enable caching** - Avoid reprocessing same forms

---

## Next Steps

1. ✅ **Set up Ollama** - Get local OCR running
2. ✅ **Test with sample forms** - Verify extraction quality
3. 📝 **Annotate 50-100 forms** - Collect training data
4. 🎯 **Train custom model** - Fine-tune TrOCR/Donut
5. 🚀 **Deploy to production** - Process 150,000 pages

For questions or issues, check:
- `backend/ocr/ollama_provider.py` - Ollama implementation
- `backend/utils/ai_form_parser.py` - Form parsing logic
- `backend/api/routes/annotation.py` - Annotation API

