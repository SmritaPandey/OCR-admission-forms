# Training CRAFT + TR-OCR on Student Admission Forms

## Overview

Yes! The CRAFT + TR-OCR models **can be trained on your student admission forms**. This guide shows you exactly how to do it.

## Quick Answer

**The training scripts are generic** - they can train on ANY data you provide. To train on student forms:

1. **Export your verified student forms** from the database
2. **Convert to training format** (JSON with image paths and text)
3. **Train the model** using the training script

## Step-by-Step Process

### Step 1: Verify Forms in Your System

First, make sure you have verified student forms in your database:

1. Upload student admission forms via the API or frontend
2. Let OCR extract the text
3. **Manually verify and correct** the extracted data
4. Save the verified forms

**Important**: Only verified forms with sufficient data will be used for training.

### Step 2: Prepare Training Data

Use the helper script to convert your verified forms to training format:

```bash
python backend/training/prepare_student_forms_training_data.py \
  training_data/student_forms_train.json \
  --min-fields 5 \
  --status verified \
  --limit 200
```

This script:
- ✅ Finds all verified forms in your database
- ✅ Extracts verified text fields from each form
- ✅ Creates image-text pairs for training
- ✅ Saves in the format needed for training

**Parameters:**
- `--min-fields 5`: Only include forms with at least 5 verified fields
- `--status verified`: Only use verified forms (most accurate)
- `--limit 200`: Use up to 200 forms (remove for all forms)

### Step 3: Split Data (Optional)

Split into train/validation sets:

```python
import json
from sklearn.model_selection import train_test_split

# Load data
with open('training_data/student_forms_train.json', 'r') as f:
    data = json.load(f)

# Split 80% train, 20% validation
train, val = train_test_split(data, test_size=0.2, random_state=42)

# Save
with open('training_data/train.json', 'w') as f:
    json.dump(train, f, indent=2)

with open('training_data/val.json', 'w') as f:
    json.dump(val, f, indent=2)
```

### Step 4: Train the Model

Train on your student forms:

```bash
python backend/training/train_craft_trocr.py \
  training_data/train.json \
  models/trocr_student_forms \
  --val-data training_data/val.json \
  --epochs 20 \
  --batch-size 8 \
  --learning-rate 5e-5 \
  --base-model microsoft/trocr-base-handwritten
```

### Step 5: Use Your Trained Model

After training, use your custom model:

```bash
# Set environment variable
export TROCR_CUSTOM_MODEL_PATH="models/trocr_student_forms"

# Or use in code
from backend.ocr.craft_trocr_provider import CraftTrocrProvider
provider = CraftTrocrProvider(custom_model_path="models/trocr_student_forms")
```

## What Gets Trained?

The model learns to recognize:
- ✅ Student names (handwritten)
- ✅ Dates of birth
- ✅ Addresses
- ✅ Phone numbers
- ✅ Course names
- ✅ Educational qualifications
- ✅ Any other handwritten text on your forms

## Data Requirements

### Minimum Requirements
- **50+ verified forms** for basic fine-tuning
- **100+ verified forms** for good results
- **200+ verified forms** for production quality

### Quality Requirements
- Forms must be **verified** (manually corrected)
- Each form should have **at least 5 verified fields**
- Images should be **clear and readable**
- **Diverse handwriting styles** for better generalization

## Complete Workflow Example

```bash
# 1. Prepare training data from database
python backend/training/prepare_student_forms_training_data.py \
  training_data/all_forms.json \
  --status verified

# 2. Split data
python -c "
import json
from sklearn.model_selection import train_test_split
data = json.load(open('training_data/all_forms.json'))
train, val = train_test_split(data, test_size=0.2, random_state=42)
json.dump(train, open('training_data/train.json', 'w'), indent=2)
json.dump(val, open('training_data/val.json', 'w'), indent=2)
print(f'Train: {len(train)}, Val: {len(val)}')
"

# 3. Train model
python backend/training/train_craft_trocr.py \
  training_data/train.json \
  models/trocr_student_forms \
  --val-data training_data/val.json \
  --epochs 20 \
  --batch-size 8

# 4. Test model
export TROCR_CUSTOM_MODEL_PATH="models/trocr_student_forms"
python test_craft_trocr.py --image test_form.jpg --model models/trocr_student_forms
```

## Training Data Format

The prepared data looks like this:

```json
[
  {
    "image_path": "uploads/training_images/form_1_page1.png",
    "text": "Student Name: John Doe\nDate of Birth: 01/01/2000\n...",
    "form_id": 1,
    "student_name": "John Doe",
    "field_count": 15,
    "verified_date": "2024-01-15T10:30:00"
  }
]
```

## Benefits of Training on Your Forms

1. **Better Accuracy**: Model learns your specific handwriting styles
2. **Domain-Specific**: Recognizes course names, field names from your forms
3. **Improved Performance**: Better than generic pre-trained model
4. **Continuous Improvement**: Retrain as you get more verified forms

## Tips for Best Results

1. **Start Small**: Begin with 50-100 forms to test the pipeline
2. **Quality Over Quantity**: Better to have 100 well-verified forms than 500 poorly verified
3. **Diverse Data**: Include forms with different handwriting styles
4. **Regular Retraining**: Retrain periodically as you verify more forms
5. **Monitor Metrics**: Watch CER/WER during training

## Troubleshooting

### "No training data generated"

**Solution**: 
- Make sure you have verified forms in the database
- Check that forms have at least 5 verified fields
- Verify that image files exist

### "Insufficient training data"

**Solution**:
- Collect more verified forms
- Lower `--min-fields` requirement (but quality may suffer)
- Use forms with status "extracted" if you don't have many verified

### "Poor training results"

**Solution**:
- Ensure data quality is high (accurate verification)
- Train for more epochs
- Use more training data
- Check learning rate

## Next Steps

1. ✅ Verify more forms in your system
2. ✅ Prepare training data
3. ✅ Train the model
4. ✅ Test on new forms
5. ✅ Deploy in production

---

**Yes, the models ARE being trained on student forms when you follow this process!** 🎓

For more details on training, see [PERFECT_TRAINING_GUIDE.md](PERFECT_TRAINING_GUIDE.md)

