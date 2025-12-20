# CRAFT-TROCR Complete Implementation Guide

## Overview

This project now includes a complete CRAFT-TROCR implementation for handwritten student admission form digitization with continuous improvement capabilities, inspired by Azure Intelligent Form Labeling.

## ✨ Key Features Implemented

### 1. CRAFT-TROCR OCR Providers

#### Combined CRAFT-TROCR Provider (`craft-trocr`)
- **Best for**: Handwritten student admission forms
- **How it works**: 
  - CRAFT detects text regions in images
  - TrOCR recognizes text in each detected region
  - Combines results for complete text extraction
- **Trainable**: Can be fine-tuned on your specific forms
- **Usage**: Set `OCR_PROVIDER=craft-trocr` in `.env`

#### CRAFT-Only Provider (`craft`)
- Text detection only (returns bounding boxes)
- Useful for getting text region locations
- Usage: Set `OCR_PROVIDER=craft` in `.env`

#### TrOCR-Only Provider (`trocr`)
- Text recognition on entire images
- Can use custom fine-tuned models
- Usage: Set `OCR_PROVIDER=trocr` in `.env`

### 2. Training Pipeline

#### Complete Training Workflow
1. **Annotate Forms**: Verify and correct forms in the browser
2. **Prepare Training Data**: Extract images and create datasets
3. **Train Model**: Fine-tune CRAFT+TrOCR on your forms
4. **Use Trained Model**: Set `TROCR_CUSTOM_MODEL_PATH` in `.env`

#### Training Scripts
- `backend/training/train_craft_trocr.py`: Complete training pipeline
- `backend/training/train_trocr.py`: Original TrOCR training (still available)
- `backend/training/prepare_data.py`: Data preparation utilities

### 3. Continuous Improvement System

#### Automatic Correction Tracking
- Tracks all corrections made during form verification
- Automatically creates training data from corrections
- Triggers retraining when enough corrections accumulate

#### Features
- **Correction Recording**: Every field correction is tracked
- **Automatic Retraining**: Retrains model when threshold reached (50+ corrections, 7+ days)
- **Model Versioning**: Maintains history of trained models
- **Incremental Learning**: Uses lower learning rate for fine-tuning

### 4. Training Interface

#### Browser-Based Training UI
- Access at: `http://localhost:5173/training`
- Features:
  - Training statistics dashboard
  - Continuous improvement metrics
  - Data preparation tools
  - Model training configuration
  - Retraining triggers

### 5. Enhanced Auto-Fill

#### Intelligent Field Mapping
- Automatically maps OCR results to form fields
- Uses pattern matching and AI parsing
- Supports 40+ student information fields
- Auto-fills during form verification

## 📦 Installation

### 1. Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install training dependencies (if not already included)
pip install transformers torch torchvision craft-text-detector
```

### 2. Configure Environment

Create or update `.env` file:

```env
# OCR Provider (use CRAFT-TROCR for handwritten forms)
OCR_PROVIDER=craft-trocr

# Enable CRAFT-TROCR providers
OCR_ENABLE_CRAFT_TROCR=true
OCR_ENABLE_CRAFT=true
OCR_ENABLE_TROCR=true

# Custom trained model (after training)
TROCR_CUSTOM_MODEL_PATH=models/trocr_student_forms_v1

# CRAFT model path (optional)
CRAFT_MODEL_PATH=models/craft_custom
```

### 3. Start Services

```bash
# Backend
python -m uvicorn backend.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

## 🚀 Usage Workflow

### Step 1: Upload and Extract Forms

1. Upload handwritten admission forms
2. System automatically extracts text using CRAFT-TROCR
3. Review extracted data in verification view

### Step 2: Verify and Correct

1. Open form for verification
2. Review auto-filled fields
3. Correct any errors
4. **Corrections are automatically tracked for training**

### Step 3: Prepare Training Data

1. Navigate to Training page (`/training`)
2. Click "Prepare Training Data"
3. Choose format (TrOCR, Donut, or Both)
4. System extracts images and creates datasets

### Step 4: Train Model

1. Configure training parameters:
   - Epochs: 10-20 (more for initial training)
   - Batch size: 8-16 (depending on GPU memory)
   - Learning rate: 5e-5 (initial), 3e-5 (fine-tuning)
2. Click "Start Training"
3. Monitor progress in terminal
4. Model saved to `uploads/models/`

### Step 5: Use Trained Model

1. Update `.env`:
   ```env
   TROCR_CUSTOM_MODEL_PATH=uploads/models/trocr_v1_20240101_120000
   ```
2. Restart backend
3. Upload new forms - they'll use your trained model!

### Step 6: Continuous Improvement

1. Continue verifying and correcting forms
2. System tracks corrections automatically
3. When 50+ corrections accumulate:
   - Navigate to Training page
   - Click "Trigger Retraining"
   - System retrains model with corrections
   - New model version created automatically

## 📊 Training Statistics

Access training statistics via API or UI:

```bash
# Get training stats
curl http://localhost:8000/api/training/stats

# Get improvement stats
curl http://localhost:8000/api/training/improvement-stats
```

## 🔧 Advanced Configuration

### Custom Base Models

```python
# In train_craft_trocr.py or via API
base_model = "microsoft/trocr-base-handwritten"  # For handwritten
base_model = "microsoft/trocr-base-printed"      # For printed text
base_model = "path/to/your/previous/model"       # For incremental training
```

### Training Parameters

- **Initial Training**: 
  - Epochs: 10-20
  - Learning Rate: 5e-5
  - Batch Size: 8-16

- **Incremental Training** (from corrections):
  - Epochs: 5-10
  - Learning Rate: 3e-5
  - Batch Size: 8

### GPU vs CPU

- **GPU Recommended**: Training is 10-50x faster
- **CPU Works**: But expect 1-6 hours for training
- Auto-detected: System uses GPU if available

## 📈 Best Practices

### 1. Annotation Quality
- Verify all fields carefully
- Correct OCR errors accurately
- More annotations = better model

### 2. Training Data
- Minimum: 50-100 annotated forms
- Recommended: 200+ annotated forms
- Optimal: 500+ annotated forms

### 3. Continuous Improvement
- Let corrections accumulate (50+ minimum)
- Retrain weekly or bi-weekly
- Monitor improvement metrics

### 4. Model Management
- Keep model versions for rollback
- Test new models before production
- Compare model performance

## 🐛 Troubleshooting

### CRAFT Not Available
```bash
pip install craft-text-detector
```

### TrOCR Not Available
```bash
pip install transformers torch torchvision
```

### CUDA Out of Memory
- Reduce batch size (4-8)
- Use gradient accumulation
- Train on CPU if needed

### Model Loading Errors
- Check `TROCR_CUSTOM_MODEL_PATH` is correct
- Ensure model files exist
- Verify model format compatibility

## 📚 API Endpoints

### Training Endpoints

- `GET /api/training/stats` - Training statistics
- `GET /api/training/improvement-stats` - Continuous improvement stats
- `POST /api/training/prepare-data` - Prepare training datasets
- `POST /api/training/start` - Start model training
- `POST /api/training/trigger-retraining` - Trigger retraining from corrections
- `GET /api/training/job/{job_id}` - Get training job status
- `GET /api/training/forms/unannotated` - Get forms needing annotation

### Annotation Endpoints

- `POST /api/annotate/{form_id}` - Save annotation
- `GET /api/annotate/{form_id}` - Get annotation
- `GET /api/export/training-data` - Export annotations

## 🎯 Performance Expectations

### OCR Accuracy
- **Base Model**: 70-85% for handwritten forms
- **Trained Model**: 85-95% for handwritten forms (after training)
- **Fine-tuned Model**: 90-98% for specific form types

### Training Time
- **50 forms**: 30-60 minutes (GPU), 2-4 hours (CPU)
- **200 forms**: 1-2 hours (GPU), 6-12 hours (CPU)
- **500 forms**: 2-4 hours (GPU), 12-24 hours (CPU)

## 🔄 Continuous Improvement Workflow

1. **Daily**: Verify forms, corrections tracked automatically
2. **Weekly**: Check improvement stats, trigger retraining if ready
3. **Monthly**: Review model performance, adjust training parameters
4. **Quarterly**: Major model retraining with all accumulated data

## 📝 Notes

- Corrections are tracked automatically during form verification
- Training data is prepared automatically from annotations
- Models are versioned and can be rolled back
- Continuous improvement happens in background
- No manual intervention needed for correction tracking

## 🎉 Success!

Your system now has:
- ✅ CRAFT-TROCR OCR for handwritten forms
- ✅ Complete training pipeline
- ✅ Continuous improvement system
- ✅ Browser-based training interface
- ✅ Automatic correction tracking
- ✅ Model versioning and management

Happy training! 🚀
