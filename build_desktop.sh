#!/bin/bash

set -e

echo "========================================"
echo "Building Desktop App for Windows"
echo "========================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed or not in PATH"
    echo "Please install Python 3.8+ and add it to PATH"
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "ERROR: Node.js is not installed or not in PATH"
    echo "Please install Node.js 18+ and add it to PATH"
    exit 1
fi

echo "Step 1: Installing Python dependencies..."
pip3 install -r requirements.txt

echo ""
echo "Step 2: Installing PyInstaller..."
pip3 install pyinstaller

echo ""
echo "Step 3: Building Python backend with PyInstaller..."
mkdir -p backend-dist
pyinstaller --clean build_backend.spec

# Copy the built executable
if [ -f "dist/api" ] || [ -f "dist/api.exe" ]; then
    mkdir -p backend-dist
    if [ -f "dist/api.exe" ]; then
        cp dist/api.exe backend-dist/api.exe
        echo "Backend executable copied to backend-dist/api.exe"
    elif [ -f "dist/api" ]; then
        cp dist/api backend-dist/api
        echo "Backend executable copied to backend-dist/api"
    fi
else
    echo "ERROR: Backend executable not found"
    exit 1
fi

echo ""
echo "Step 4: Installing frontend dependencies..."
cd frontend
npm install

echo ""
echo "Step 5: Building frontend with Vite..."
npm run build
cd ..

echo ""
echo "Step 6: Installing Electron dependencies..."
cd electron
npm install
cd ..

echo ""
echo "Step 7: Building Electron app..."
cd electron
npm run dist
cd ..

echo ""
echo "========================================"
echo "Build Complete!"
echo "========================================"
echo ""
echo "The installer can be found in: electron/dist/"
echo ""
