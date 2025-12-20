#!/bin/bash
# Quick OCR Test Script

echo "=========================================="
echo "Quick OCR Test"
echo "=========================================="
echo ""

# Find test image
TEST_IMAGE=""
if [ -f "data/samples/images/jatin_page_01.png" ]; then
    TEST_IMAGE="data/samples/images/jatin_page_01.png"
elif [ -f "test_form.png" ]; then
    TEST_IMAGE="test_form.png"
else
    echo "❌ No test image found"
    echo "   Please provide a test image path"
    exit 1
fi

echo "📄 Test image: $TEST_IMAGE"
echo ""

# Test Ollama
echo "Testing Ollama with llama3.2-vision..."
python3 test_ocr_providers.py "$TEST_IMAGE" --ollama-only

echo ""
echo "✅ Test complete!"
echo ""
echo "To test all providers:"
echo "  python3 test_ocr_providers.py \"$TEST_IMAGE\" --all"
