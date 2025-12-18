@echo off
REM Complete setup script for Windows - Installs everything needed

echo ==========================================
echo Complete OCR Training System Setup
echo ==========================================
echo.

REM Step 1: Install training dependencies
echo Step 1/4: Installing training dependencies...
if exist "install_training_dependencies.bat" (
    call install_training_dependencies.bat
) else (
    echo install_training_dependencies.bat not found, running manual installation...
    python -m venv venv
    call venv\Scripts\activate.bat
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt -r requirements-training.txt
)

echo.
echo Step 2/4: Checking Tesseract OCR installation...
echo.

REM Check if Tesseract is installed
where tesseract >nul 2>&1
if %errorlevel% equ 0 (
    echo Tesseract found:
    tesseract --version | findstr /i "tesseract"
) else (
    echo Tesseract not found.
    echo Please install Tesseract from:
    echo https://github.com/UB-Mannheim/tesseract/wiki
    echo.
    echo After installation, add to PATH or set environment variable:
    echo set TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
)

echo.
echo Step 3/4: Creating necessary directories...
if not exist "uploads\training_data" mkdir uploads\training_data
if not exist "uploads\training_data\images" mkdir uploads\training_data\images
if not exist "models" mkdir models
if not exist "logs" mkdir logs

echo Directories created
echo.

echo Step 4/4: Setting up .env file...
if not exist ".env" (
    if exist ".env.example" (
        copy .env.example .env
        echo Created .env file from .env.example
        echo Please edit .env file with your configuration
    ) else (
        echo Creating basic .env file...
        (
            echo # Database
            echo DATABASE_URL=sqlite:///./admission_forms.db
            echo.
            echo # OCR Provider
            echo OCR_PROVIDER=tesseract-google-combined
            echo OCR_ENABLE_TESSERACT=true
            echo OCR_ENABLE_GOOGLE_VISION=true
            echo OCR_ENABLE_TESSERACT_GOOGLE_COMBINED=true
            echo.
            echo # File Upload
            echo UPLOAD_DIR=uploads
            echo MAX_FILE_SIZE=10485760
            echo.
            echo # CORS
            echo CORS_ORIGINS=http://localhost:3000,http://localhost:5173
        ) > .env
        echo Created basic .env file
    )
) else (
    echo .env file already exists
)

echo.
echo ==========================================
echo Setup Complete!
echo ==========================================
echo.
echo Next steps:
echo 1. Activate virtual environment: venv\Scripts\activate
echo 2. Edit .env file with your configuration (if needed)
echo 3. Start the server: python -m uvicorn backend.main:app --reload
echo 4. Run training: python backend\scripts\quick_train.py
echo.
echo For detailed instructions, see:
echo   - INSTALL_ALL_DEPENDENCIES.md
echo   - COMPLETE_TRAINING_GUIDE.md
echo.
pause
