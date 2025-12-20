#!/bin/bash
# One-command training script for student forms
# Analyzes, prepares data, and trains the best model

set -e

echo "=========================================="
echo "Student Forms OCR Training"
echo "=========================================="
echo ""

# Check if we're in the right directory
if [ ! -f "backend/training/train_best_model.py" ]; then
    echo "❌ Error: Please run this script from the project root directory"
    exit 1
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed"
    exit 1
fi

echo "Step 1: Analyzing your verified forms..."
echo "----------------------------------------"
python3 backend/training/train_best_model.py --analyze-only

echo ""
echo "Step 2: Preparing training data with field mappings..."
echo "----------------------------------------"
python3 backend/training/train_best_model.py --prepare-only \
  --output-data training_data/student_forms.json

echo ""
echo "Step 3: Training the best model..."
echo "----------------------------------------"
echo "This may take 1-6 hours depending on your system..."
echo ""

python3 backend/training/train_best_model.py \
  --training-data training_data/student_forms.json \
  --output-model models/trocr_student_forms \
  --model-type auto \
  --epochs 20 \
  --batch-size 8

echo ""
echo "=========================================="
echo "✅ Training Complete!"
echo "=========================================="
echo ""
echo "To use your trained model:"
echo "  1. Add to .env file:"
echo "     TROCR_CUSTOM_MODEL_PATH=models/trocr_student_forms"
echo ""
echo "  2. Or set environment variable:"
echo "     export TROCR_CUSTOM_MODEL_PATH='models/trocr_student_forms'"
echo ""
echo "  3. Restart backend server"
echo ""
echo "Your trained model will now auto-fill form fields accurately! 🎉"
