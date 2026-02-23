@echo off
echo ========================================
echo Building Desktop App for Windows
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ and add it to PATH
    pause
    exit /b 1
)

REM Check if Node.js is installed
node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js is not installed or not in PATH
    echo Please install Node.js 18+ and add it to PATH
    pause
    exit /b 1
)

echo Step 1: Installing Python dependencies...
echo Note: tesserocr is optional and may fail if Tesseract is not installed
echo This is OK - the app will work without it
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo WARNING: Some dependencies may have failed to install
    echo This might be OK if optional packages like tesserocr failed
    echo Continuing with build...
)

echo.
echo Step 2: Installing PyInstaller...
pip install pyinstaller
if errorlevel 1 (
    echo ERROR: Failed to install PyInstaller
    pause
    exit /b 1
)

echo.
echo Step 3: Building Python backend with PyInstaller...
if not exist "backend-dist" mkdir backend-dist
python -m PyInstaller --clean build_backend.spec
if errorlevel 1 (
    echo ERROR: Failed to build backend
    pause
    exit /b 1
)

REM Copy the built executable
if exist "dist\api.exe" (
    if not exist "backend-dist" mkdir backend-dist
    copy /Y "dist\api.exe" "backend-dist\api.exe"
    echo Backend executable copied to backend-dist\api.exe
) else (
    echo ERROR: Backend executable not found in dist\api.exe
    pause
    exit /b 1
)

echo.
echo Step 4: Installing frontend dependencies...
cd frontend
call npm install
if errorlevel 1 (
    echo ERROR: Failed to install frontend dependencies
    cd ..
    pause
    exit /b 1
)

echo.
echo Step 5: Building frontend with Vite...
echo Note: Building without TypeScript type checking for faster build
call npm run build
if errorlevel 1 (
    echo ERROR: Failed to build frontend
    cd ..
    pause
    exit /b 1
)
cd ..

echo.
echo Step 6: Installing Electron dependencies...
cd electron
call npm install
if errorlevel 1 (
    echo ERROR: Failed to install Electron dependencies
    cd ..
    pause
    exit /b 1
)
cd ..

echo.
echo Step 7: Building Electron app...
cd electron
call npm run dist
if errorlevel 1 (
    echo ERROR: Failed to build Electron app
    cd ..
    pause
    exit /b 1
)
cd ..

echo.
echo ========================================
echo Build Complete!
echo ========================================
echo.
echo The installer can be found in: electron\dist\
echo.
pause
