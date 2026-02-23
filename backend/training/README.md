# OCR Model Training

This directory contains scripts for fine-tuning OCR models on your specific form dataset.

## Overview

- **TrOCR** - Best for handwritten text recognition
- **Donut** - Best for structured form understanding with layout awareness
- **Data Preparation** - Convert annotations to training format
- **Evaluation** - Test trained models with metrics (CER, WER, accuracy)

## Prerequisites

### macOS Installation

**For macOS users, see `README_MACOS.md` for detailed macOS-specific instructions.**

Quick setup for macOS:

```bash
# Install system dependencies
brew install libjpeg libpng libtiff

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install PyTorch (Apple Silicon MPS support included)
pip install torch torchvision torchaudio

# Install training dependencies
pip install transformers datasets accelerate pillow
```

### Linux/Windows Installation

Install training dependencies:

```bash
pip install transformers torch torchvision datasets accelerate
```

For GPU training (Linux/Windows):
- CUDA-compatible GPU
- PyTorch with CUDA support

## Quick Start

### macOS Users

**See `README_MACOS.md` for complete macOS-specific instructions.**

Quick start for macOS:

```bash
# 1. Setup environment
python3 -m venv venv
source venv/bin/activate
pip install torch torchvision transformers datasets accelerate

# 2. Export annotations
curl http://127.0.0.1:8000/api/export/training-data?format=json > annotations.json

# 3. Prepare data
cd backend/training
python3 prepare_data.py ../../annotations.json --format both --split

# 4. Train TrOCR (use smaller batch size on macOS)
python3 train_trocr.py \
  ../uploads/training_data/train.json \
  ../models/trocr_finetuned \
  --val-data ../uploads/training_data/val.json \
  --epochs 10 \
  --batch-size 4 \
  --base-model microsoft/trocr-base-handwritten

# 5. Evaluate
python3 evaluate_model.py \
  ../models/trocr_finetuned \
  ../uploads/training_data/test.json
```

### Linux/Windows Users

### 1. Collect Annotations

First, annotate your forms via the API or frontend:

```bash
# Export annotations
curl http://127.0.0.1:8000/api/export/training-data?format=json > annotations.json
```

### 2. Prepare Training Data

Convert annotations to training format:

```bash
cd backend/training

# Prepare data for both TrOCR and Donut
python prepare_data.py ../uploads/training_data/annotations.json \
  --format both \
  --split
```

This will:
- Extract images from form files
- Create TrOCR dataset (`trocr_dataset.json`)
- Create Donut dataset (`donut_dataset.json`)
- Split into train/val/test sets

### 3. Train TrOCR Model

```bash
python train_trocr.py \
  train.json \
  ../models/trocr_finetuned \
  --val-data val.json \
  --epochs 10 \
  --batch-size 8 \
  --learning-rate 5e-5
```

### 4. Train Donut Model

```bash
python train_donut.py \
  train.json \
  ../models/donut_finetuned \
  --val-data val.json \
  --epochs 15 \
  --batch-size 4 \
  --learning-rate 3e-5
```

### 5. Evaluate Model

```bash
python evaluate_model.py \
  ../models/trocr_finetuned \
  test.json \
  --output evaluation_report.json
```

## Detailed Usage

### Data Preparation

```bash
python prepare_data.py <annotations_json> [options]

Options:
  --format {trocr,donut,both}  Output format (default: both)
  --output-dir DIR             Output directory
  --split                      Split into train/val/test sets
```

**Output:**
- `images/` - Extracted form images
- `trocr_dataset.json` - TrOCR training data
- `donut_dataset.json` - Donut training data
- `train.json`, `val.json`, `test.json` - Split datasets (if --split)

### TrOCR Training

```bash
python train_trocr.py <training_data> <output_model> [options]

Required:
  training_data    Path to training JSON file
  output_model     Path to save fine-tuned model

Options:
  --val-data PATH          Validation dataset path
  --epochs N               Number of epochs (default: 10)
  --batch-size N           Batch size (default: 8)
  --learning-rate FLOAT    Learning rate (default: 5e-5)
  --base-model MODEL       Base model (default: microsoft/trocr-base-printed)
  --max-length N           Max sequence length (default: 128)
  --save-steps N           Steps between checkpoints (default: 500)
  --eval-steps N           Steps between evaluations (default: 500)
```

**Base Models:**
- `microsoft/trocr-base-printed` - For printed text
- `microsoft/trocr-base-handwritten` - For handwritten text (recommended for forms)

### Donut Training

```bash
python train_donut.py <training_data> <output_model> [options]

Required:
  training_data    Path to training JSON file
  output_model     Path to save fine-tuned model

Options:
  --val-data PATH          Validation dataset path
  --epochs N               Number of epochs (default: 15)
  --batch-size N           Batch size (default: 4, smaller due to memory)
  --learning-rate FLOAT     Learning rate (default: 3e-5)
  --base-model MODEL       Base model (default: naver-clova-ix/donut-base)
  --max-length N           Max sequence length (default: 768)
```

**Note:** Donut requires more GPU memory. Use smaller batch sizes or gradient accumulation.

### Model Evaluation

```bash
python evaluate_model.py <model_path> <test_data> [options]

Required:
  model_path    Path to trained model
  test_data     Path to test JSON file

Options:
  --output PATH    Save evaluation report to file
  --device {cuda,cpu}  Device to use
```

**Metrics:**
- **CER (Character Error Rate)** - Lower is better
- **WER (Word Error Rate)** - Lower is better
- **Accuracy** - Exact match accuracy, higher is better

## Training Data Format

### TrOCR Format

```json
[
  {
    "image_path": "path/to/image.png",
    "text": "Student Name: John Doe\nDate of Birth: 01/01/2000"
  }
]
```

### Donut Format

```json
[
  {
    "image_path": "path/to/image.png",
    "ground_truth": "{\"student_name\": \"John Doe\", \"date_of_birth\": \"01/01/2000\"}"
  }
]
```

## Using Trained Models

### TrOCR

```python
from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from PIL import Image

# Load model
model = VisionEncoderDecoderModel.from_pretrained("models/trocr_finetuned")
processor = TrOCRProcessor.from_pretrained("models/trocr_finetuned")

# Process image
image = Image.open("form.png").convert('RGB')
pixel_values = processor(image, return_tensors="pt").pixel_values

# Generate text
generated_ids = model.generate(pixel_values)
text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
```

### Donut

```python
from transformers import DonutProcessor, VisionEncoderDecoderModel
from PIL import Image

# Load model
model = VisionEncoderDecoderModel.from_pretrained("models/donut_finetuned")
processor = DonutProcessor.from_pretrained("models/donut_finetuned")

# Process image
image = Image.open("form.png").convert('RGB')
pixel_values = processor(image, return_tensors="pt").pixel_values

# Generate JSON
task_prompt = "<s_cord-v2>"
decoder_input_ids = processor.tokenizer(
    task_prompt, add_special_tokens=False, return_tensors="pt"
).input_ids

outputs = model.generate(
    pixel_values,
    decoder_input_ids=decoder_input_ids,
    max_length=model.decoder.config.max_position_embeddings,
    early_stopping=True,
    pad_token_id=processor.tokenizer.pad_token_id,
    eos_token_id=processor.tokenizer.eos_token_id,
    use_cache=True,
    num_beams=1,
    bad_words_ids=[[processor.tokenizer.unk_token_id]],
    return_dict_in_generate=True,
)

sequence = processor.batch_decode(outputs.sequences)[0]
sequence = sequence.replace(processor.tokenizer.eos_token, "").replace(processor.tokenizer.pad_token, "")
sequence = sequence.replace(task_prompt, "")

# Parse JSON
import json
result = json.loads(sequence)
```

## Tips for Better Results

1. **Collect More Data**
   - Minimum: 50-100 annotated forms
   - Recommended: 200+ forms for better accuracy

2. **Data Quality**
   - Ensure accurate annotations
   - Include diverse handwriting styles
   - Cover all form variations

3. **Training Parameters**
   - Start with default parameters
   - Adjust learning rate if loss doesn't decrease
   - Use validation set to prevent overfitting
   - **macOS**: Use smaller batch sizes (4 for TrOCR, 2 for Donut)

4. **Model Selection**
   - **TrOCR**: Use `trocr-base-handwritten` for handwritten forms
   - **Donut**: Better for structured forms with layout

5. **Hardware**
   - **macOS**: Apple Silicon (M1/M2/M3) with MPS provides good acceleration
   - **Linux/Windows**: GPU highly recommended (especially for Donut)
   - 16GB+ RAM for Donut training
   - 8GB+ RAM for TrOCR training

## Troubleshooting

**Out of Memory:**
- Reduce batch size
- Use gradient accumulation
- Reduce image resolution

**Poor Accuracy:**
- Collect more training data
- Improve annotation quality
- Try different base models
- Adjust learning rate

**Training Too Slow:**
- Use GPU instead of CPU
- Reduce batch size if memory limited
- Use mixed precision (fp16)

## Next Steps

After training:
1. Evaluate on test set
2. Compare with baseline models
3. Deploy trained model
4. Integrate into OCR provider system

See `TRAINING_AND_IMPROVEMENT_GUIDE.md` for more details.
