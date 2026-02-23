@echo off
echo Checking build requirements...
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [X] Python is NOT installed or not in PATH
    echo     Please install Python 3.8+ from https://www.python.org/downloads/
    set MISSING=1
) else (
    python --version
    echo [✓] Python is installed
)

REM Check Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo [X] Node.js is NOT installed or not in PATH
    echo     Please install Node.js 18+ from https://nodejs.org/
    set MISSING=1
) else (
    node --version
    echo [✓] Node.js is installed
)

REM Check npm
npm --version >nul 2>&1
if errorlevel 1 (
    echo [X] npm is NOT installed or not in PATH
    set MISSING=1
) else (
    npm --version
    echo [✓] npm is installed
)

REM Check pip
pip --version >nul 2>&1
if errorlevel 1 (
    echo [X] pip is NOT installed
    echo     This usually comes with Python
    set MISSING=1
) else (
    pip --version
    echo [✓] pip is installed
)

echo.
if defined MISSING (
    echo ========================================
    echo Some requirements are missing!
    echo Please install the missing components and try again.
    echo ========================================
    pause
    exit /b 1
) else (
    echo ========================================
    echo All requirements are met!
    echo You can now run build_desktop.bat
    echo ========================================
    pause
)
