# Perfect PyTorch Training Guide for CRAFT + TR-OCR

## 🎯 Overview

This guide covers the **perfect PyTorch training setup** for fine-tuning TR-OCR models on your handwritten text data. The training script includes all best practices for production-ready model training.

## ✨ Key Features

### 1. Advanced Evaluation Metrics
- **CER (Character Error Rate)**: Measures character-level accuracy
- **WER (Word Error Rate)**: Measures word-level accuracy  
- **Accuracy**: Overall recognition accuracy
- Automatic calculation during validation

### 2. Learning Rate Scheduling
- **Cosine Annealing**: Smooth learning rate decay (default)
- **Linear**: Linear decay
- **Polynomial**: Polynomial decay
- **Constant**: Fixed learning rate

### 3. Advanced Data Augmentation
- Contrast adjustment
- Brightness adjustment
- Sharpening
- Color saturation
- Small rotations (±2 degrees)
- Light noise injection

### 4. Training Optimizations
- **Gradient Clipping**: Prevents exploding gradients
- **AdamW Optimizer**: Better weight decay handling
- **Mixed Precision (FP16)**: 2x faster on GPU
- **Gradient Accumulation**: Simulate larger batch sizes

### 5. Model Management
- **Checkpointing**: Saves models during training
- **Best Model Selection**: Automatically loads best model
- **Resume Training**: Continue from checkpoints
- **Metadata Tracking**: Saves all training parameters

## 🚀 Quick Start

### Basic Training

```bash
python backend/training/train_craft_trocr.py \
  train.json \
  models/my_model \
  --epochs 20 \
  --batch-size 8 \
  --learning-rate 5e-5
```

### Advanced Training (GPU)

```bash
python backend/training/train_craft_trocr.py \
  train.json \
  models/my_model \
  --val-data val.json \
  --epochs 30 \
  --batch-size 16 \
  --learning-rate 3e-5 \
  --fp16 \
  --gradient-accumulation 2 \
  --lr-scheduler cosine \
  --save-steps 250 \
  --eval-steps 250
```

## 📊 Understanding Metrics

### Character Error Rate (CER)
- Measures character-level accuracy
- Lower is better (0.0 = perfect)
- Formula: `(Substitutions + Deletions + Insertions) / Total Characters`

### Word Error Rate (WER)
- Measures word-level accuracy
- Lower is better (0.0 = perfect)
- Formula: `(Substitutions + Deletions + Insertions) / Total Words`

### Accuracy
- Overall recognition accuracy
- Higher is better (1.0 = perfect)
- Formula: `1.0 - CER`

### Example Output

```
Final validation loss: 0.1234
Character Error Rate (CER): 0.0456
Word Error Rate (WER): 0.1234
Accuracy: 0.9544
```

## 🎓 Training Best Practices

### 1. Data Preparation

**Minimum Requirements:**
- 100+ samples for fine-tuning
- 200+ samples for better results
- 500+ samples for production quality

**Data Quality:**
- Accurate text annotations
- High-resolution images (300+ DPI)
- Diverse handwriting styles
- Various image qualities

### 2. Hyperparameter Tuning

| Parameter | Recommended Range | Notes |
|-----------|-------------------|-------|
| `learning_rate` | 3e-5 to 5e-5 | Start with 5e-5, reduce if overfitting |
| `batch_size` | 4-16 | GPU: 8-16, CPU: 4-8 |
| `epochs` | 15-30 | Monitor validation loss |
| `warmup_steps` | 500-1000 | 10% of total steps |
| `weight_decay` | 0.01 | Standard regularization |

### 3. Learning Rate Schedulers

**Cosine (Recommended):**
- Smooth decay
- Better convergence
- Good for most cases

**Linear:**
- Steady decay
- Good for long training

**Polynomial:**
- Customizable decay
- For specific schedules

### 4. Monitoring Training

**Watch for:**
- Training loss decreasing
- Validation loss decreasing
- CER/WER improving
- No overfitting (val loss not increasing)

**Signs of Overfitting:**
- Training loss decreases, validation loss increases
- High training accuracy, low validation accuracy
- **Solution**: Reduce learning rate, add more data, use augmentation

## 📈 Training Workflow

### Step 1: Prepare Data

```bash
# Convert your data to JSON format
python backend/training/prepare_craft_trocr_data.py csv data.csv images/ train.json

# Validate data
python backend/training/prepare_craft_trocr_data.py validate train.json --image-dir images/
```

### Step 2: Split Data

```python
import json
from sklearn.model_selection import train_test_split

data = json.load(open('train.json'))
train, val = train_test_split(data, test_size=0.2, random_state=42)

json.dump(train, open('train_split.json', 'w'), indent=2)
json.dump(val, open('val_split.json', 'w'), indent=2)
```

### Step 3: Train Model

```bash
python backend/training/train_craft_trocr.py \
  train_split.json \
  models/trocr_prescriptions \
  --val-data val_split.json \
  --epochs 20 \
  --batch-size 8 \
  --learning-rate 5e-5 \
  --lr-scheduler cosine
```

### Step 4: Monitor Training

Training logs are saved to `checkpoints/logs/`. Monitor with:

```bash
# View in terminal (if using tensorboard)
tensorboard --logdir models/trocr_prescriptions/checkpoints/logs
```

### Step 5: Evaluate Model

```bash
# Test on sample images
python test_craft_trocr.py --image test.jpg --model models/trocr_prescriptions
```

## 🔧 Advanced Features

### Resume Training

If training is interrupted:

```bash
python backend/training/train_craft_trocr.py \
  train.json \
  models/my_model \
  --resume models/my_model/checkpoints/checkpoint-1000
```

### Early Stopping

Prevent overfitting by stopping when validation loss stops improving:

```bash
python backend/training/train_craft_trocr.py \
  train.json \
  models/my_model \
  --early-stopping-patience 3
```

### Mixed Precision Training

Faster training on GPU (2x speedup):

```bash
python backend/training/train_craft_trocr.py \
  train.json \
  models/my_model \
  --fp16
```

### Gradient Accumulation

Simulate larger batch sizes:

```bash
# Effective batch size = batch_size * gradient_accumulation
python backend/training/train_craft_trocr.py \
  train.json \
  models/my_model \
  --batch-size 4 \
  --gradient-accumulation 4  # Effective batch size = 16
```

## 📊 Training Output

### Console Output

```
==================================================
CRAFT + TR-OCR Perfect Training
==================================================
Training data: train.json
Output model: models/my_model
Base model: microsoft/trocr-base-handwritten
Epochs: 20, Batch size: 8, LR: 5e-05
Max length: 128, Augmentation: True

✅ Using GPU: NVIDIA GeForce RTX 3090
   CUDA Version: 11.8
   GPU Memory: 24.00 GB

Loading TR-OCR processor and model...
✅ Model loaded: microsoft/trocr-base-handwritten
   Total parameters: 558,000,000
   Trainable parameters: 558,000,000

Loading training dataset...
✅ Training samples: 1000
✅ Validation samples: 200

Training configuration:
   Steps per epoch: 125
   Total steps: 2500
   Save steps: 500
   Eval steps: 500

==================================================
Starting Training...
==================================================

[Training progress...]

==================================================
✅ Training Complete!
==================================================
Final training loss: 0.1234
Final validation loss: 0.1456
Character Error Rate (CER): 0.0456
Word Error Rate (WER): 0.1234
Accuracy: 0.9544
```

### Saved Files

```
models/my_model/
├── config.json              # Model configuration
├── pytorch_model.bin        # Model weights
├── preprocessor_config.json # Processor config
├── tokenizer_config.json    # Tokenizer config
├── vocab.json              # Vocabulary
├── merges.txt              # BPE merges
└── training_metadata.json   # Training info
```

## 🎯 Performance Tips

### 1. GPU Training
- Use `--fp16` for 2x speedup
- Increase batch size (8-16)
- Use gradient accumulation for larger effective batches

### 2. CPU Training
- Reduce batch size (4-8)
- Disable FP16
- Use fewer workers

### 3. Apple Silicon (MPS)
- Works out of the box
- Batch size 4-8 recommended
- No FP16 support yet

### 4. Memory Optimization
- Reduce batch size if OOM
- Use gradient accumulation
- Reduce image size in preprocessing

## 🐛 Troubleshooting

### Issue: CUDA Out of Memory

**Solutions:**
```bash
# Reduce batch size
--batch-size 4

# Use gradient accumulation
--gradient-accumulation 2

# Disable FP16 (uses less memory)
# Remove --fp16 flag
```

### Issue: Training Loss Not Decreasing

**Solutions:**
1. Check learning rate (try 1e-5 or 3e-5)
2. Verify data quality
3. Check data format
4. Ensure images load correctly

### Issue: Overfitting

**Solutions:**
1. Reduce learning rate
2. Add more training data
3. Enable data augmentation
4. Use early stopping
5. Increase weight decay

### Issue: Poor Validation Metrics

**Solutions:**
1. Train for more epochs
2. Use more diverse training data
3. Adjust learning rate
4. Check data quality

## 📚 Example Training Scripts

### Small Dataset (100 samples)

```bash
python backend/training/train_craft_trocr.py \
  train.json \
  models/small_model \
  --epochs 15 \
  --batch-size 4 \
  --learning-rate 5e-5 \
  --val-split 0.2
```

### Large Dataset (1000+ samples)

```bash
python backend/training/train_craft_trocr.py \
  train.json \
  models/large_model \
  --val-data val.json \
  --epochs 30 \
  --batch-size 16 \
  --learning-rate 3e-5 \
  --fp16 \
  --lr-scheduler cosine \
  --save-steps 250 \
  --eval-steps 250
```

### Production Training

```bash
python backend/training/train_craft_trocr.py \
  train.json \
  models/production_model \
  --val-data val.json \
  --epochs 50 \
  --batch-size 16 \
  --learning-rate 3e-5 \
  --fp16 \
  --gradient-accumulation 2 \
  --lr-scheduler cosine \
  --early-stopping-patience 5 \
  --save-steps 100 \
  --eval-steps 100 \
  --warmup-steps 1000
```

## ✅ Training Checklist

- [ ] Data prepared and validated
- [ ] Train/validation split created
- [ ] Appropriate batch size selected
- [ ] Learning rate chosen
- [ ] GPU/CPU configured
- [ ] Training started
- [ ] Metrics monitored
- [ ] Best model selected
- [ ] Model tested on new data

## 🎉 Success Criteria

Your model is ready when:
- ✅ Validation loss is decreasing
- ✅ CER < 0.1 (90%+ character accuracy)
- ✅ WER < 0.3 (70%+ word accuracy)
- ✅ No overfitting (val loss tracks train loss)
- ✅ Good performance on test images

---

**Happy Training! 🚀**

For more details, see [CRAFT_TROCR_GUIDE.md](CRAFT_TROCR_GUIDE.md)

