#!/bin/bash
# Train all OCR providers starting with CRAFT+TR-OCR (best pipeline)

set -e

echo "=========================================="
echo "Training All OCR Providers"
echo "Starting with CRAFT+TR-OCR (Best Pipeline)"
echo "=========================================="
echo ""

# Check if we're in the right directory
if [ ! -f "backend/training/train_craft_trocr.py" ]; then
    echo "❌ Error: Please run this script from the project root directory"
    exit 1
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed"
    exit 1
fi

echo "Step 1: Preparing training data from images..."
echo "----------------------------------------"
echo "Processing 185 images with Tesseract..."
python3 backend/scripts/prepare_training_from_images_simple.py

echo ""
echo "Step 2: Checking training data..."
echo "----------------------------------------"
if [ ! -f "training_data/student_forms.json" ]; then
    echo "❌ Error: Training data not found"
    exit 1
fi

SAMPLE_COUNT=$(python3 -c "import json; print(len(json.load(open('training_data/student_forms.json'))))")
echo "✅ Found $SAMPLE_COUNT training samples"

if [ "$SAMPLE_COUNT" -lt 10 ]; then
    echo "⚠️  Warning: Less than 10 samples. Training may not be effective."
    echo "   Consider processing more images or verifying the data."
fi

echo ""
echo "Step 3: Training CRAFT+TR-OCR (Best Pipeline) ⭐"
echo "----------------------------------------"
echo "This is the BEST pipeline for handwritten forms!"
echo "Training may take 1-6 hours depending on your system..."
echo ""

python3 backend/training/train_craft_trocr.py \
  training_data/student_forms.json \
  models/trocr_student_forms \
  --epochs 20 \
  --batch-size 8 \
  --image-dir . \
  --base-model microsoft/trocr-base-handwritten \
  --learning-rate 5e-5 \
  --val-split 0.2

echo ""
echo "=========================================="
echo "✅ CRAFT+TR-OCR Training Complete!"
echo "=========================================="
echo ""
echo "Model saved to: models/trocr_student_forms"
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
echo "Your trained CRAFT+TR-OCR model will now provide accurate OCR! 🎉"
echo ""
echo "=========================================="
echo "Next: Train other providers (optional)"
echo "=========================================="
echo ""
echo "Other providers that can be trained:"
echo "  - CRAFT (text detection) - Uses pre-trained weights"
echo "  - TR-OCR (text recognition) - Same as above"
echo "  - Tesseract - Can train custom language model (advanced)"
echo ""
