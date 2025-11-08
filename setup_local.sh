#!/bin/bash

# Student Records Management System - Local Setup Script
# Installs all dependencies and sets up the system

set -e  # Exit on error

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Student Records Management System - Setup Script        ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Python
if ! command_exists python3; then
    echo -e "${RED}❌ Python 3 not found. Please install Python 3.8 or higher.${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}✅ Python found: $PYTHON_VERSION${NC}"

# Check pip
if ! command_exists pip3; then
    echo -e "${RED}❌ pip3 not found. Please install pip.${NC}"
    exit 1
fi

# Install Python dependencies
echo -e "${BLUE}Installing Python dependencies...${NC}"
pip3 install -r requirements.txt

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Python dependencies installed${NC}"
else
    echo -e "${RED}❌ Failed to install Python dependencies${NC}"
    exit 1
fi

# Check and install Tesseract OCR
echo -e "${BLUE}Checking Tesseract OCR...${NC}"
if command_exists tesseract; then
    TESSERACT_VERSION=$(tesseract --version 2>&1 | head -n 1)
    echo -e "${GREEN}✅ Tesseract found: $TESSERACT_VERSION${NC}"
else
    echo -e "${YELLOW}⚠️  Tesseract OCR not found.${NC}"
    echo -e "${BLUE}Installation instructions:${NC}"
    echo "  Ubuntu/Debian: sudo apt-get install tesseract-ocr"
    echo "  macOS:          brew install tesseract"
    echo "  Windows:        Download from https://github.com/UB-Mannheim/tesseract/wiki"
    echo ""
    read -p "Continue without Tesseract? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check Node.js
if ! command_exists node; then
    echo -e "${RED}❌ Node.js not found. Please install Node.js 16 or higher.${NC}"
    echo "Download from: https://nodejs.org/"
    exit 1
fi

NODE_VERSION=$(node --version)
echo -e "${GREEN}✅ Node.js found: $NODE_VERSION${NC}"

# Check npm
if ! command_exists npm; then
    echo -e "${RED}❌ npm not found. Please install npm.${NC}"
    exit 1
fi

NPM_VERSION=$(npm --version)
echo -e "${GREEN}✅ npm found: $NPM_VERSION${NC}"

# Install frontend dependencies
echo -e "${BLUE}Installing frontend dependencies...${NC}"
cd frontend
npm install
cd ..

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Frontend dependencies installed${NC}"
else
    echo -e "${RED}❌ Failed to install frontend dependencies${NC}"
    exit 1
fi

# Create uploads directory
mkdir -p uploads
echo -e "${GREEN}✅ Created uploads directory${NC}"

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        echo -e "${GREEN}✅ Created .env file from .env.example${NC}"
        echo -e "${YELLOW}⚠️  Please edit .env file with your OCR provider credentials${NC}"
    else
        echo -e "${YELLOW}⚠️  .env.example not found. Create .env manually if needed.${NC}"
    fi
fi

# Summary
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✅ Setup Complete!                                        ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "  1. Run test script:    python3 test_system.py"
echo "  2. Start the system:  ./run_local.sh"
echo "  3. Open browser:      http://localhost:5173"
echo ""
echo -e "${YELLOW}Optional: Configure cloud OCR providers in .env file${NC}"
echo "  See SETUP_OCR.md for detailed instructions"
echo ""
