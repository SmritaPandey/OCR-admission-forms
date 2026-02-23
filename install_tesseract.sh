#!/bin/bash
# Tesseract Installation Script for macOS

echo "=== Tesseract OCR Installation ==="
echo ""

# Check if already installed
if command -v tesseract &> /dev/null; then
    echo "✅ Tesseract is already installed!"
    tesseract --version
    exit 0
fi

echo "Tesseract is not installed. Please choose an installation method:"
echo ""
echo "1. Homebrew (Recommended) - Requires admin access"
echo "2. MacPorts - Requires admin access"
echo "3. Manual download instructions"
echo "4. Use AI providers instead (no installation needed)"
echo ""
echo "For Homebrew installation, run:"
echo "  /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
echo "  brew install tesseract"
echo ""
echo "For AI providers, see INSTALL_TESSERACT.md"
