#!/bin/bash
# Complete Test and Training Workflow

set -e

echo "=========================================="
echo "OCR Test & Training Workflow"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Step 1: Test Ollama
echo -e "${GREEN}Step 1: Testing Ollama with llama3.2-vision${NC}"
echo "----------------------------------------"
if command -v ollama &> /dev/null; then
    echo "✅ Ollama is installed"
    
    # Check if model is available
    if ollama list | grep -q "llama3.2-vision"; then
        echo "✅ llama3.2-vision model is available"
    else
        echo "⚠️  llama3.2-vision not found, pulling..."
        ollama pull llama3.2-vision
    fi
    
    # Check if Ollama is running
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "✅ Ollama is running"
    else
        echo "⚠️  Ollama is not running. Starting in background..."
        ollama serve > /dev/null 2>&1 &
        sleep 5
    fi
else
    echo "❌ Ollama is not installed"
    echo "   Install: https://ollama.ai"
    exit 1
fi

# Step 2: Test OCR Providers
echo ""
echo -e "${GREEN}Step 2: Testing OCR Providers${NC}"
echo "----------------------------------------"

# Find a test image
TEST_IMAGE=""
if [ -f "data/samples/images/jatin_page_01.png" ]; then
    TEST_IMAGE="data/samples/images/jatin_page_01.png"
elif [ -f "test_form.png" ]; then
    TEST_IMAGE="test_form.png"
else
    echo "⚠️  No test image found. Please provide one:"
    read -p "Enter image path: " TEST_IMAGE
fi

if [ -f "$TEST_IMAGE" ]; then
    echo "📄 Test image: $TEST_IMAGE"
    echo ""
    echo "Testing Ollama specifically..."
    python3 test_ocr_providers.py "$TEST_IMAGE" --ollama-only
    
    echo ""
    read -p "Test all providers? (y/n): " test_all
    if [ "$test_all" = "y" ]; then
        python3 test_ocr_providers.py "$TEST_IMAGE" --all
    fi
else
    echo "❌ Test image not found: $TEST_IMAGE"
fi

# Step 3: Check Annotated Forms
echo ""
echo -e "${GREEN}Step 3: Checking Annotated Forms${NC}"
echo "----------------------------------------"
python3 -c "
from backend.database import SessionLocal, AdmissionForm
db = SessionLocal()
forms = db.query(AdmissionForm).filter(
    AdmissionForm.status == 'verified',
    AdmissionForm.additional_info.isnot(None)
).all()
annotated = [f for f in forms if f.additional_info and 'annotation' in f.additional_info]
print(f'✅ Found {len(annotated)} annotated forms')
db.close()
"

# Step 4: Prepare Training Data
echo ""
echo -e "${GREEN}Step 4: Preparing Training Data${NC}"
echo "----------------------------------------"
python3 prepare_training_from_annotations.py

# Step 5: Train CRAFT+TR-OCR
echo ""
echo -e "${GREEN}Step 5: Training CRAFT+TR-OCR${NC}"
echo "----------------------------------------"

if [ -f "training_data/annotated_forms_training.json" ]; then
    SAMPLE_COUNT=$(python3 -c "import json; print(len(json.load(open('training_data/annotated_forms_training.json'))))")
    echo "✅ Training data ready: $SAMPLE_COUNT samples"
    
    if [ "$SAMPLE_COUNT" -ge 10 ]; then
        echo ""
        read -p "Start training CRAFT+TR-OCR? (y/n): " train_now
        if [ "$train_now" = "y" ]; then
            echo "🚀 Starting training..."
            python3 backend/training/train_craft_trocr.py \
                training_data/annotated_forms_training.json \
                models/trocr_trained \
                --epochs 20 \
                --batch-size 8 \
                --image-dir . \
                --base-model microsoft/trocr-base-handwritten
        else
            echo "⏭️  Skipping training. Run manually when ready:"
            echo "   python3 backend/training/train_craft_trocr.py training_data/annotated_forms_training.json models/trocr_trained --epochs 20"
        fi
    else
        echo "⚠️  Not enough samples ($SAMPLE_COUNT). Need at least 10 for training."
        echo "   Please verify more forms to create annotations."
    fi
else
    echo "❌ Training data not found. Run Step 4 first."
fi

echo ""
echo "=========================================="
echo "✅ Workflow Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Verify more forms in the browser (creates annotations automatically)"
echo "  2. Run: python3 prepare_training_from_annotations.py"
echo "  3. Train: python3 backend/training/train_craft_trocr.py training_data/annotated_forms_training.json models/trocr_trained --epochs 20"
echo ""
