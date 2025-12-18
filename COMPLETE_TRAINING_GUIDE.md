# Complete Training Guide for Student Admission Forms OCR

This guide will help you train world-class OCR models specifically for your student admission forms, including text fields and multiple choice questions (checkboxes).

## Table of Contents

1. [Quick Start Workflow](#quick-start-workflow)
2. [Step-by-Step Training Process](#step-by-step-training-process)
3. [Labeling Forms (Key-Value Extraction)](#labeling-forms)
4. [Training Data Collection](#training-data-collection)
5. [Model Training](#model-training)
6. [Checkbox Detection Training](#checkbox-detection-training)
7. [API Reference](#api-reference)
8. [Best Practices](#best-practices)

---

## Quick Start Workflow

### 1. Upload Your Filled Forms

```bash
# Upload forms via API
curl -X POST http://localhost:8000/api/upload \
  -F "file=@form1.pdf" \
  -F "ocr_provider=tesseract-google-combined"

# Or upload multiple forms
curl -X POST http://localhost:8000/api/batch-upload \
  -F "files=@form1.pdf" \
  -F "files=@form2.pdf" \
  -F "files=@form3.pdf"
```

### 2. Auto-Label Forms (Quick Start)

```bash
# Auto-extract labels from OCR results
curl -X POST "http://localhost:8000/api/auto-label/1?save_annotation=true"

# Bulk auto-label multiple forms
curl -X POST "http://localhost:8000/api/auto-label/bulk" \
  -H "Content-Type: application/json" \
  -d '{"form_ids": [1, 2, 3, 4, 5], "save_annotations": true}'
```

### 3. Prepare Training Data

```bash
# Prepare data for training
curl -X POST "http://localhost:8000/api/training/prepare-data?format=both&split=true"
```

### 4. Train Model

```bash
# Start training (uses prepared data)
curl -X POST "http://localhost:8000/api/training/start" \
  -H "Content-Type: application/json" \
  -d '{
    "model_type": "trocr",
    "epochs": 10,
    "batch_size": 8,
    "learning_rate": 5e-5
  }'
```

---

## Step-by-Step Training Process

### Phase 1: Data Collection (Week 1-2)

#### Goal: Collect 100-200 annotated forms

**Step 1.1: Upload Forms**
- Upload all your filled admission forms (PDF or images)
- Use the combined Tesseract+Google Vision provider for best initial OCR
- Verify OCR results are reasonable

**Step 1.2: Auto-Label (Initial Pass)**
```bash
# Get list of unannotated forms
curl http://localhost:8000/api/training/forms/unannotated?limit=100

# Auto-label all forms
for form_id in {1..100}; do
  curl -X POST "http://localhost:8000/api/auto-label/$form_id?save_annotation=true"
done
```

**Step 1.3: Manual Review & Correction**
- Review auto-labeled forms via the frontend verification interface
- Correct any mistakes in field values
- Add missing fields
- Verify checkbox states

### Phase 2: Manual Annotation (Week 2-3)

#### Goal: High-quality annotations with bounding boxes

**For each form:**

1. **Access form via API:**
```bash
curl http://localhost:8000/api/annotate/1
```

2. **Create comprehensive annotation:**
```bash
curl -X POST http://localhost:8000/api/annotate/1 \
  -H "Content-Type: application/json" \
  -d '{
    "form_id": 1,
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
      },
      {
        "label": "OBC Category",
        "checked": false,
        "bounding_box": {"x": 50, "y": 230, "width": 20, "height": 20},
        "page_number": 1
      }
    ],
    "notes": "Form clearly filled with good handwriting"
  }'
```

### Phase 3: Training Data Preparation (Week 3)

**Step 3.1: Check Training Statistics**
```bash
curl http://localhost:8000/api/training/stats
```

**Step 3.2: Export Annotations**
```bash
# Export as JSON
curl http://localhost:8000/api/export/training-data?format=json > annotations.json

# Export with training-ready formats
curl -X POST "http://localhost:8000/api/training/prepare-data?format=both&split=true"
```

**Step 3.3: Verify Training Data**
- Check `uploads/training_data/` directory
- Verify images are extracted
- Check train/val/test splits

### Phase 4: Model Training (Week 4)

**Step 4.1: Train TrOCR Model**
```bash
cd backend/training

# Activate virtual environment
source ../../venv/bin/activate

# Train model
python train_trocr.py \
  ../uploads/training_data/train.json \
  ../models/trocr_finetuned \
  --val-data ../uploads/training_data/val.json \
  --epochs 10 \
  --batch-size 8 \
  --learning-rate 5e-5 \
  --base-model microsoft/trocr-base-handwritten
```

**Step 4.2: Train Donut Model (for structured understanding)**
```bash
python train_donut.py \
  ../uploads/training_data/train.json \
  ../models/donut_finetuned \
  --val-data ../uploads/training_data/val.json \
  --epochs 15 \
  --batch-size 4 \
  --learning-rate 3e-5
```

**Step 4.3: Evaluate Models**
```bash
python evaluate_model.py \
  ../models/trocr_finetuned \
  ../uploads/training_data/test.json \
  --output evaluation_report.json
```

### Phase 5: Integration & Deployment (Week 5)

**Step 5.1: Integrate Trained Model**
- Update OCR provider to use trained model
- Test on new forms
- Compare accuracy with baseline

**Step 5.2: Continuous Improvement**
- Add more forms to training data
- Retrain periodically
- Monitor accuracy metrics

---

## Labeling Forms

### Method 1: Auto-Labeling (Fastest)

Auto-labeling extracts key-value pairs from existing OCR results:

```bash
# Preview what will be extracted
curl http://localhost:8000/api/auto-label/preview/1

# Save auto-extracted labels
curl -X POST "http://localhost:8000/api/auto-label/1?save_annotation=true"

# Bulk auto-label
curl -X POST "http://localhost:8000/api/auto-label/bulk" \
  -H "Content-Type: application/json" \
  -d '{
    "form_ids": [1, 2, 3, 4, 5],
    "save_annotations": true
  }'
```

**Advantages:**
- Very fast (processes 100 forms in minutes)
- Good starting point
- Extracts from existing OCR results

**Limitations:**
- May miss some fields
- Checkbox detection may need manual verification
- No bounding boxes (can be added manually later)

### Method 2: Manual Annotation (Most Accurate)

Manual annotation gives you full control and bounding boxes:

```bash
curl -X POST http://localhost:8000/api/annotate/1 \
  -H "Content-Type: application/json" \
  -d '{
    "form_id": 1,
    "fields": [
      {
        "field_name": "student_name",
        "value": "John Doe",
        "bounding_box": {"x": 100, "y": 50, "width": 200, "height": 30},
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
    ]
  }'
```

**Key-Value Pairs:**
- Each field becomes a key-value pair automatically
- Field name = key
- Field value = value
- Stored in `key_value_pairs` in annotation

**Checkbox States:**
- Label = checkbox text/description
- Checked = true/false
- Bounding box = location on form

### Method 3: Hybrid Approach (Recommended)

1. **Auto-label first** (quick pass)
2. **Manual review** (verify accuracy)
3. **Add missing fields** (complete annotation)
4. **Add bounding boxes** (for better training)

---

## Training Data Collection

### Minimum Requirements

- **50 forms**: Minimum viable dataset
- **100 forms**: Good accuracy
- **200+ forms**: Excellent accuracy
- **500+ forms**: Production-grade accuracy

### Data Quality Checklist

- [ ] All forms are clearly scanned (300+ DPI)
- [ ] All fields are annotated
- [ ] All checkboxes are marked
- [ ] Bounding boxes are accurate (if provided)
- [ ] Values are correctly transcribed
- [ ] Forms represent diverse handwriting styles
- [ ] Forms represent all form variations (if multiple templates)

### Getting Forms for Annotation

```bash
# Get unannotated forms
curl "http://localhost:8000/api/training/forms/unannotated?limit=50"

# Check annotation progress
curl http://localhost:8000/api/training/stats
```

---

## Model Training

### TrOCR Training (Recommended for Handwriting)

TrOCR (Transformer-based OCR) is excellent for handwritten text:

```bash
cd backend/training

python train_trocr.py \
  ../uploads/training_data/train.json \
  ../models/trocr_finetuned \
  --val-data ../uploads/training_data/val.json \
  --epochs 10 \
  --batch-size 8 \
  --learning-rate 5e-5 \
  --base-model microsoft/trocr-base-handwritten
```

**Parameters:**
- `epochs`: Number of training iterations (10-20)
- `batch_size`: Samples per batch (4-8 on CPU, 16-32 on GPU)
- `learning_rate`: Learning rate (5e-5 recommended)
- `base_model`: `trocr-base-handwritten` (handwriting) or `trocr-base-printed` (printed)

### Donut Training (Recommended for Structured Forms)

Donut (Document Understanding Transformer) understands form structure:

```bash
python train_donut.py \
  ../uploads/training_data/train.json \
  ../models/donut_finetuned \
  --val-data ../uploads/training_data/val.json \
  --epochs 15 \
  --batch-size 4 \
  --learning-rate 3e-5
```

**Advantages:**
- Understands form layout
- Can extract structured JSON directly
- Good for key-value extraction
- Handles checkboxes well

### Training via API

```bash
curl -X POST "http://localhost:8000/api/training/start" \
  -H "Content-Type: application/json" \
  -d '{
    "model_type": "trocr",
    "epochs": 10,
    "batch_size": 8,
    "learning_rate": 5e-5,
    "base_model": "microsoft/trocr-base-handwritten"
  }'
```

---

## Checkbox Detection Training

### Understanding Checkboxes

Checkboxes are detected in two ways:

1. **Text-based detection**: Looking for [x], ✓, ☑ in OCR text
2. **Visual detection**: Using AI vision models to see filled boxes

### Annotation Format for Checkboxes

```json
{
  "checkboxes": [
    {
      "label": "General Category",
      "checked": true,
      "bounding_box": {"x": 50, "y": 200, "width": 20, "height": 20},
      "page_number": 1
    }
  ]
}
```

### Training Data for Checkboxes

Checkboxes are included in:
- **TrOCR dataset**: As text (e.g., "General Category: ✓")
- **Donut dataset**: In ground truth JSON (e.g., `{"checkboxes": {"General Category": true}}`)

### Improving Checkbox Detection

1. **Annotate more checkboxes** in training data
2. **Use visual detection** (AI vision models)
3. **Train on checkbox-specific patterns**
4. **Combine text + visual detection**

---

## API Reference

### Training Statistics
```bash
GET /api/training/stats
```
Returns statistics about annotated forms, fields, and checkboxes.

### Prepare Training Data
```bash
POST /api/training/prepare-data?format=both&split=true
```
Prepares training data with images and labels.

### Export Training Data
```bash
GET /api/export/training-data?format=json
POST /api/training/export-annotations?format=trocr&include_images=true
```
Export annotations in various formats.

### Auto-Label Forms
```bash
POST /api/auto-label/{form_id}?save_annotation=true
POST /api/auto-label/bulk
```
Automatically extract labels from OCR results.

### Save Annotation
```bash
POST /api/annotate/{form_id}
GET /api/annotate/{form_id}
```
Save and retrieve form annotations.

### Get Unannotated Forms
```bash
GET /api/training/forms/unannotated?limit=50
```
Get list of forms that need annotation.

---

## Best Practices

### 1. Data Collection
- Start with auto-labeling to get initial annotations quickly
- Manually review and correct auto-labels
- Aim for at least 100 annotated forms
- Include diverse handwriting styles
- Include all form variations

### 2. Annotation Quality
- Double-check field values for accuracy
- Verify checkbox states (checked/unchecked)
- Add bounding boxes when possible (improves training)
- Use consistent field names across forms
- Add notes for unusual cases

### 3. Training
- Start with smaller epochs (5-10) to test
- Use validation set to prevent overfitting
- Monitor training loss and validation metrics
- Save checkpoints during training
- Compare multiple model configurations

### 4. Evaluation
- Test on held-out test set
- Measure accuracy on key fields
- Test checkbox detection separately
- Compare with baseline models
- Document improvements

### 5. Continuous Improvement
- Add new forms to training data regularly
- Retrain models periodically
- Track accuracy over time
- Address common error patterns
- Update model when form templates change

---

## Troubleshooting

### Low Annotation Coverage
**Problem**: Only a few forms are annotated
**Solution**: Use bulk auto-labeling first, then manually review

### Poor Training Accuracy
**Problem**: Model accuracy is low
**Solutions**:
- Collect more training data (aim for 200+ forms)
- Improve annotation quality
- Try different base models
- Adjust learning rate
- Use data augmentation

### Checkbox Detection Issues
**Problem**: Checkboxes not detected accurately
**Solutions**:
- Use AI vision models (Ollama, GPT-4 Vision)
- Annotate more checkboxes with bounding boxes
- Combine text + visual detection
- Train specifically on checkbox patterns

### Training Takes Too Long
**Problem**: Training is slow
**Solutions**:
- Use GPU if available
- Reduce batch size
- Reduce number of epochs (test with 5 first)
- Use smaller base model
- Train on subset first

---

## Next Steps

1. ✅ **Upload your filled forms** (100-200 forms)
2. ✅ **Auto-label all forms** (quick start)
3. ✅ **Manually review and correct** (ensure quality)
4. ✅ **Prepare training data** (extract images and labels)
5. ✅ **Train TrOCR model** (for handwriting)
6. ✅ **Train Donut model** (for structure)
7. ✅ **Evaluate models** (test on held-out data)
8. ✅ **Deploy trained models** (integrate into system)
9. ✅ **Monitor and improve** (continuous improvement)

---

## Support

For issues or questions:
- Check `TRAINING_AND_IMPROVEMENT_GUIDE.md` for detailed instructions
- Review API documentation at `/docs`
- Check training logs for errors
- Verify data format matches expected structure
