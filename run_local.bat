@echo off
REM Student Records Management System - Local Run Script (Windows)
REM Starts both backend and frontend servers

setlocal enabledelayedexpansion

echo ╔════════════════════════════════════════════════════════════╗
echo ║  Student Records Management System - Local Run Script     ║
echo ╚════════════════════════════════════════════════════════════╝
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found. Please install Python 3.8 or higher.
    exit /b 1
)

REM Check Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Node.js not found. Please install Node.js 16 or higher.
    exit /b 1
)

REM Check npm
npm --version >nul 2>&1
if errorlevel 1 (
    echo ❌ npm not found. Please install npm.
    exit /b 1
)

REM Check Python dependencies
echo Checking Python dependencies...
python -c "import fastapi" >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Python dependencies not installed.
    set /p install_py="Install Python dependencies now? (y/n): "
    if /i "!install_py!"=="y" (
        echo Installing Python dependencies...
        pip install -r requirements.txt
    ) else (
        echo ❌ Cannot start backend without dependencies.
        exit /b 1
    )
)

REM Check frontend dependencies
echo Checking frontend dependencies...
if not exist "frontend\node_modules" (
    echo ⚠️  Frontend dependencies not installed.
    set /p install_npm="Install frontend dependencies now? (y/n): "
    if /i "!install_npm!"=="y" (
        echo Installing frontend dependencies...
        cd frontend
        call npm install
        cd ..
    ) else (
        echo ❌ Cannot start frontend without dependencies.
        exit /b 1
    )
)

REM Create uploads directory
if not exist "uploads" mkdir uploads

REM Start backend
echo Starting backend server on http://localhost:8000...
start "Backend Server" cmd /k "python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000"

REM Wait a bit for backend to start
timeout /t 3 /nobreak >nul

REM Start frontend
echo Starting frontend server on http://localhost:5173...
cd frontend
start "Frontend Server" cmd /k "npm run dev"
cd ..

REM Wait a bit for frontend to start
timeout /t 3 /nobreak >nul

REM Success message
echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║  ✅ System is running!                                     ║
echo ╚════════════════════════════════════════════════════════════╝
echo.
echo Backend API:  http://localhost:8000
echo API Docs:     http://localhost:8000/docs
echo Frontend:     http://localhost:5173
echo.
echo Close the command windows to stop the servers.
echo.
pause
