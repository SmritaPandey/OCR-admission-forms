@echo off
REM Installation script for OCR Training Dependencies (Windows)
REM This script installs all dependencies needed for training OCR models

echo ==========================================
echo OCR Training Dependencies Installation
echo ==========================================
echo.

REM Check Python version
echo Checking Python version...
python --version
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo Python found!
echo.

REM Create virtual environment if it doesn't exist
echo ==========================================
echo Setting up Python Virtual Environment
echo ==========================================

if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    echo Virtual environment created
) else (
    echo Virtual environment already exists
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Virtual environment activated
echo.

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip setuptools wheel

echo pip upgraded
echo.

REM Install PyTorch
echo ==========================================
echo Installing PyTorch
echo ==========================================
echo Installing PyTorch (CPU version)...
echo Note: If you have CUDA GPU, install PyTorch with CUDA support from pytorch.org
python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

echo PyTorch installed
echo.

REM Install training dependencies
echo ==========================================
echo Installing Training Dependencies
echo ==========================================

python -m pip install ^
    transformers>=4.36.0 ^
    datasets>=2.16.0 ^
    accelerate>=0.25.0 ^
    pillow>=10.0.0 ^
    numpy>=1.24.0 ^
    scikit-learn>=1.3.0 ^
    tqdm>=4.65.0 ^
    tensorboard>=2.14.0

echo Training dependencies installed
echo.

REM Install OCR and image processing dependencies
echo ==========================================
echo Installing OCR Dependencies
echo ==========================================

python -m pip install ^
    pytesseract>=0.3.10 ^
    pdf2image>=1.16.3 ^
    PyMuPDF>=1.23.0 ^
    opencv-python>=4.8.0 ^
    numpy>=1.24.0

echo OCR dependencies installed
echo.

REM Install API dependencies
echo ==========================================
echo Installing API Dependencies
echo ==========================================

python -m pip install ^
    fastapi>=0.100.0 ^
    uvicorn[standard]>=0.23.0 ^
    python-multipart>=0.0.6 ^
    pydantic>=2.0.0 ^
    pydantic-settings>=2.0.0 ^
    sqlalchemy>=2.0.0 ^
    requests>=2.31.0

echo API dependencies installed
echo.

REM Optional cloud OCR dependencies
echo ==========================================
echo Optional Cloud OCR Dependencies
echo ==========================================
echo.
echo The following are optional and only needed if using cloud OCR providers:
echo.
echo Google Cloud Vision: pip install google-cloud-vision
echo Google Document AI: pip install google-cloud-documentai
echo Azure Form Recognizer: pip install azure-ai-formrecognizer
echo AWS Textract: pip install boto3
echo.
set /p install_cloud="Would you like to install cloud OCR dependencies? (y/n): "
if /i "%install_cloud%"=="y" (
    echo.
    echo Installing cloud OCR dependencies...
    python -m pip install ^
        google-cloud-vision>=3.7.0 ^
        google-cloud-documentai>=2.20.0 ^
        azure-ai-formrecognizer>=3.3.0 ^
        azure-cognitiveservices-vision-computervision>=0.9.0 ^
        boto3>=1.34.0
    echo Cloud OCR dependencies installed
) else (
    echo Skipping cloud OCR dependencies
)

echo.

REM Verify installations
echo ==========================================
echo Verifying Installations
echo ==========================================

python -c "import torch; print('PyTorch', torch.__version__)" 2>nul || echo ERROR: PyTorch not installed correctly
python -c "import transformers; print('Transformers', transformers.__version__)" 2>nul || echo ERROR: Transformers not installed
python -c "import datasets; print('Datasets', datasets.__version__)" 2>nul || echo ERROR: Datasets not installed
python -c "import PIL; print('Pillow', PIL.__version__)" 2>nul || echo ERROR: Pillow not installed
python -c "import fastapi; print('FastAPI', fastapi.__version__)" 2>nul || echo ERROR: FastAPI not installed

echo.
echo ==========================================
echo Installation Complete!
echo ==========================================
echo.
echo Next steps:
echo 1. Activate the virtual environment: venv\Scripts\activate
echo 2. Install Tesseract OCR from https://github.com/UB-Mannheim/tesseract/wiki
echo 3. Set up your .env file with configuration
echo 4. Run the training script: python backend\scripts\quick_train.py
echo.
echo For detailed instructions, see COMPLETE_TRAINING_GUIDE.md
pause
