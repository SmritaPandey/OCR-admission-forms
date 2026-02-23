# =============================================================================
# Student Admission Form OCR System - Unified Startup Script (Windows)
# =============================================================================

$ErrorActionPreference = "Continue"

$PROJECT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $PROJECT_DIR

# Ports
$BACKEND_PORT = 8000
$FRONTEND_PORT = 5173

function Print-Header {
    Write-Host ""
    Write-Host "================================================================" -ForegroundColor Cyan
    Write-Host "       Student Admission Form OCR System                    " -ForegroundColor Cyan
    Write-Host "================================================================" -ForegroundColor Cyan
    Write-Host ""
}

function Test-Command {
    param([string]$Command)
    try {
        $null = Get-Command $Command -ErrorAction Stop
        return $true
    } catch {
        return $false
    }
}

function Test-PortInUse {
    param([int]$Port)
    try {
        $connection = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
        if ($null -ne $connection) { return $true }
    } catch {
        # Fallback: try to create a listener to test if port is available
        try {
            $listener = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Any, $Port)
            $listener.Start()
            $listener.Stop()
            return $false
        } catch {
            return $true
        }
    }
    return $false
}

function Stop-ProcessOnPort {
    param([int]$Port)
    try {
        $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
        if ($connections) {
            $processes = $connections | Select-Object -ExpandProperty OwningProcess -Unique
            foreach ($pid in $processes) {
                try {
                    Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
                } catch {
                    # Process may already be stopped
                }
            }
        }
    } catch {
        # Fallback: use netstat to find processes
        try {
            $netstatOutput = netstat -ano | Select-String ":$Port\s+.*LISTENING"
            if ($netstatOutput) {
                foreach ($line in $netstatOutput) {
                    if ($line -match '\s+(\d+)$') {
                        $processId = [int]$matches[1]
                        try {
                            Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
                        } catch {
                            # Process may already be stopped
                        }
                    }
                }
            }
        } catch {
            # Ignore errors
        }
    }
}

function Get-PythonCommand {
    if (Test-Command "python") {
        return "python"
    } elseif (Test-Command "py") {
        return "py"
    } elseif (Test-Command "python3") {
        return "python3"
    }
    return $null
}

function Check-Prerequisites {
    Write-Host "Checking prerequisites..." -ForegroundColor Cyan
    
    # Check Python
    $pythonCmd = Get-PythonCommand
    if ($null -eq $pythonCmd) {
        Write-Host "[X] Python not found. Please install Python 3.8+" -ForegroundColor Red
        exit 1
    }
    try {
        $pythonVersion = & $pythonCmd --version 2>&1 | Out-String
        Write-Host "[OK] Python: $pythonVersion" -ForegroundColor Green
    } catch {
        Write-Host "[X] Python not working properly" -ForegroundColor Red
        exit 1
    }
    
    # Check Node.js
    if (-not (Test-Command "node")) {
        Write-Host "[X] Node.js not found. Please install Node.js 16+" -ForegroundColor Red
        exit 1
    }
    $nodeVersion = node --version
    Write-Host "[OK] Node.js: $nodeVersion" -ForegroundColor Green
    
    # Check npm
    if (-not (Test-Command "npm")) {
        Write-Host "[X] npm not found" -ForegroundColor Red
        exit 1
    }
    $npmVersion = npm --version
    Write-Host "[OK] npm: $npmVersion" -ForegroundColor Green
    
    # Check Tesseract (optional)
    if (Test-Command "tesseract") {
        Write-Host "[OK] Tesseract OCR available" -ForegroundColor Green
    } else {
        Write-Host "[!] Tesseract not found (optional - other OCR providers available)" -ForegroundColor Yellow
    }
}

function Setup-System {
    Print-Header
    Write-Host "Setting up the system..." -ForegroundColor Cyan
    Write-Host ""
    
    Check-Prerequisites
    Write-Host ""
    
    # Python dependencies
    $pythonCmd = Get-PythonCommand
    Write-Host "Installing Python dependencies..." -ForegroundColor Cyan
    & $pythonCmd -m pip install -q -r requirements.txt
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] Python dependencies installed" -ForegroundColor Green
    } else {
        Write-Host "[!] Python dependencies installation had issues" -ForegroundColor Yellow
    }
    
    # Frontend dependencies
    Write-Host "Installing frontend dependencies..." -ForegroundColor Cyan
    Push-Location frontend
    npm install --silent
    Pop-Location
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] Frontend dependencies installed" -ForegroundColor Green
    } else {
        Write-Host "[!] Frontend dependencies installation had issues" -ForegroundColor Yellow
    }
    
    # Create directories
    if (-not (Test-Path "uploads")) { 
        New-Item -ItemType Directory -Path "uploads" -Force | Out-Null 
    }
    if (-not (Test-Path "training_data")) { 
        New-Item -ItemType Directory -Path "training_data" -Force | Out-Null 
    }
    Write-Host "[OK] Created required directories" -ForegroundColor Green
    
    # Create .env if needed
    if (-not (Test-Path ".env") -and (Test-Path ".env.example")) {
        Copy-Item ".env.example" ".env"
        Write-Host "[OK] Created .env from .env.example" -ForegroundColor Green
        Write-Host "  → Edit .env to configure OCR providers" -ForegroundColor Yellow
    }
    
    # Initialize database
    Write-Host "Initializing database..." -ForegroundColor Cyan
    try {
        $output = & $pythonCmd -c "from backend.database import engine, Base; Base.metadata.create_all(bind=engine)" 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[OK] Database initialized" -ForegroundColor Green
        }
    } catch {
        # Database may already be initialized
        Write-Host "[OK] Database initialized (or already exists)" -ForegroundColor Green
    }
    
    Write-Host ""
    Write-Host "================================================================" -ForegroundColor Green
    Write-Host "  [OK] Setup Complete!                                        " -ForegroundColor Green
    Write-Host "================================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Run " -NoNewline
    Write-Host ".\start.ps1 start" -ForegroundColor Yellow -NoNewline
    Write-Host " to launch the application"
}

function Stop-Services {
    Write-Host "Stopping services..." -ForegroundColor Yellow
    
    # Kill by PID files
    if (Test-Path ".backend.pid") {
        try {
            $processId = [int](Get-Content ".backend.pid" -ErrorAction SilentlyContinue)
            if ($processId) {
                Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
            }
        } catch {
            # Process may already be stopped
        }
        Remove-Item ".backend.pid" -ErrorAction SilentlyContinue
    }
    
    if (Test-Path ".frontend.pid") {
        try {
            $processId = [int](Get-Content ".frontend.pid" -ErrorAction SilentlyContinue)
            if ($processId) {
                Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
            }
        } catch {
            # Process may already be stopped
        }
        Remove-Item ".frontend.pid" -ErrorAction SilentlyContinue
    }
    
    # Kill any remaining on ports
    Stop-ProcessOnPort -Port $BACKEND_PORT
    Stop-ProcessOnPort -Port $FRONTEND_PORT
    
    Write-Host "[OK] Services stopped" -ForegroundColor Green
}

function Start-Backend {
    Write-Host "Starting backend server..." -ForegroundColor Cyan
    
    # Check port
    if (Test-PortInUse -Port $BACKEND_PORT) {
        Write-Host "Port $BACKEND_PORT in use, stopping existing process..." -ForegroundColor Yellow
        Stop-ProcessOnPort -Port $BACKEND_PORT
        Start-Sleep -Seconds 1
    }
    
    # Start uvicorn using Start-Process with proper configuration
    $pythonCmd = Get-PythonCommand
    $logFile = Join-Path $PROJECT_DIR "backend.log"
    $batchFile = Join-Path $PROJECT_DIR "start_backend_temp.bat"
    
    try {
        # Test if Python command works first
        $testResult = & $pythonCmd -m uvicorn --help 2>&1
        if ($LASTEXITCODE -ne 0 -and $testResult -notlike "*usage*") {
            Write-Host "[X] Python/uvicorn not available. Error: $testResult" -ForegroundColor Red
            return
        }
        
        # Create a temporary batch file to run the backend with proper redirection
        $pythonPath = (Get-Command $pythonCmd).Source
        $batchContent = "@echo off`r`n`"$pythonPath`" -m uvicorn backend.main:app --reload --host 0.0.0.0 --port $BACKEND_PORT > `"$logFile`" 2>&1"
        Set-Content -Path $batchFile -Value $batchContent -Encoding ASCII
        
        # Start the batch file
        $process = Start-Process -FilePath $batchFile `
            -WorkingDirectory $PROJECT_DIR `
            -WindowStyle Hidden `
            -PassThru
        
        if ($process) {
            # Wait a moment for Python process to start
            Start-Sleep -Seconds 3
            
            # Find the actual Python process running uvicorn
            $pythonProcess = $null
            $processes = Get-Process | Where-Object { $_.ProcessName -like "*python*" } -ErrorAction SilentlyContinue
            foreach ($proc in $processes) {
                try {
                    $cmdLine = (Get-WmiObject Win32_Process -Filter "ProcessId = $($proc.Id)" -ErrorAction SilentlyContinue).CommandLine
                    if ($cmdLine -and $cmdLine -like "*uvicorn*backend.main*") {
                        $pythonProcess = $proc
                        break
                    }
                } catch {
                    # Ignore errors getting command line
                }
            }
            
            if ($pythonProcess) {
                $pythonProcess.Id | Out-File -FilePath ".backend.pid" -Encoding ASCII -NoNewline
                Write-Host "  Backend process started (PID: $($pythonProcess.Id))" -ForegroundColor Gray
            } else {
                # Fallback: save cmd.exe PID if we can't find Python process yet
                $process.Id | Out-File -FilePath ".backend.pid" -Encoding ASCII -NoNewline
                Write-Host "  Backend process starting (checking for Python process)..." -ForegroundColor Gray
                
                # Wait a bit more and check again
                Start-Sleep -Seconds 2
                $processes = Get-Process | Where-Object { $_.ProcessName -like "*python*" } -ErrorAction SilentlyContinue
                foreach ($proc in $processes) {
                    try {
                        $cmdLine = (Get-WmiObject Win32_Process -Filter "ProcessId = $($proc.Id)" -ErrorAction SilentlyContinue).CommandLine
                        if ($cmdLine -and $cmdLine -like "*uvicorn*backend.main*") {
                            $pythonProcess = $proc
                            $pythonProcess.Id | Out-File -FilePath ".backend.pid" -Encoding ASCII -NoNewline
                            break
                        }
                    } catch {
                        # Ignore errors
                    }
                }
                
                if (-not $pythonProcess) {
                    Write-Host "[X] Backend process exited immediately. Check $logFile for errors." -ForegroundColor Red
                    if (Test-Path $logFile) {
                        Start-Sleep -Seconds 1  # Give it a moment to write
                        $errorContent = Get-Content $logFile -ErrorAction SilentlyContinue
                        if ($errorContent) {
                            Write-Host "  Error log:" -ForegroundColor Yellow
                            $errorContent | ForEach-Object { Write-Host "    $_" -ForegroundColor Gray }
                        } else {
                            Write-Host "  Log file is empty - command may have failed before writing." -ForegroundColor Yellow
                            Write-Host "  Trying to run command directly to see error..." -ForegroundColor Yellow
                            $directTest = & $pythonCmd -m uvicorn backend.main:app --reload --host 0.0.0.0 --port $BACKEND_PORT 2>&1 | Select-Object -First 5
                            if ($directTest) {
                                Write-Host "  Direct test output:" -ForegroundColor Yellow
                                $directTest | ForEach-Object { Write-Host "    $_" -ForegroundColor Gray }
                            }
                        }
                    } else {
                        Write-Host "  No log file created - command failed to execute." -ForegroundColor Yellow
                        Write-Host "  Trying to run command directly to see error..." -ForegroundColor Yellow
                        $directTest = & $pythonCmd -m uvicorn backend.main:app --reload --host 0.0.0.0 --port $BACKEND_PORT 2>&1 | Select-Object -First 5
                        if ($directTest) {
                            Write-Host "  Direct test output:" -ForegroundColor Yellow
                            $directTest | ForEach-Object { Write-Host "    $_" -ForegroundColor Gray }
                        }
                    }
                    # Clean up temp batch file
                    if (Test-Path $batchFile) { Remove-Item $batchFile -ErrorAction SilentlyContinue }
                    return
                }
            }
        } else {
            Write-Host "[X] Failed to start backend process" -ForegroundColor Red
            return
        }
    } catch {
        Write-Host "[X] Failed to start backend: $_" -ForegroundColor Red
        if (Test-Path $logFile) {
            $errorContent = Get-Content $logFile -Tail 10 -ErrorAction SilentlyContinue
            if ($errorContent) {
                Write-Host "  Check $logFile for details:" -ForegroundColor Yellow
                $errorContent | ForEach-Object { Write-Host "    $_" -ForegroundColor Gray }
            }
        }
        # Clean up temp batch file
        if (Test-Path $batchFile) { Remove-Item $batchFile -ErrorAction SilentlyContinue }
        return
    }
    
    # Clean up temp batch file after successful start
    if (Test-Path $batchFile) { 
        Start-Sleep -Seconds 1
        Remove-Item $batchFile -ErrorAction SilentlyContinue 
    }
    
    # Wait a bit more for server to fully start
    Start-Sleep -Seconds 3
    
    # Check if Python process is still running
    $processId = Get-Content ".backend.pid" -ErrorAction SilentlyContinue
    if ($processId) {
        $processId = [int]$processId
        $stillRunning = Get-Process -Id $processId -ErrorAction SilentlyContinue
        if (-not $stillRunning) {
            Write-Host "[X] Backend process stopped. Check $logFile for errors." -ForegroundColor Red
            if (Test-Path $logFile) {
                $errorContent = Get-Content $logFile -ErrorAction SilentlyContinue
                if ($errorContent) {
                    Write-Host "  Error log:" -ForegroundColor Yellow
                    $errorContent | ForEach-Object { Write-Host "    $_" -ForegroundColor Gray }
                }
            }
            return
        }
    }
    
    # Try to connect to health endpoint
    $maxRetries = 5
    $retryCount = 0
    $backendRunning = $false
    
    while ($retryCount -lt $maxRetries -and -not $backendRunning) {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:$BACKEND_PORT/health" -TimeoutSec 2 -ErrorAction SilentlyContinue
            if ($response.StatusCode -eq 200) {
                Write-Host "[OK] Backend running on http://localhost:$BACKEND_PORT" -ForegroundColor Green
                $backendRunning = $true
            }
        } catch {
            $retryCount++
            if ($retryCount -lt $maxRetries) {
                Start-Sleep -Seconds 2
            }
        }
    }
    
    if (-not $backendRunning) {
        Write-Host "[!] Backend may still be starting... (check $logFile if issues persist)" -ForegroundColor Yellow
    }
}

function Start-Frontend {
    Write-Host "Starting frontend server..." -ForegroundColor Cyan
    
    # Check port
    if (Test-PortInUse -Port $FRONTEND_PORT) {
        Write-Host "Port $FRONTEND_PORT in use, stopping existing process..." -ForegroundColor Yellow
        Stop-ProcessOnPort -Port $FRONTEND_PORT
        Start-Sleep -Seconds 1
    }
    
    # Check node_modules
    if (-not (Test-Path "frontend/node_modules")) {
        Write-Host "Installing frontend dependencies..." -ForegroundColor Yellow
        Push-Location frontend
        npm install
        Pop-Location
    }
    
    # Start vite - use cmd to run npm in the frontend directory
    $frontendPath = Join-Path $PROJECT_DIR "frontend"
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = "cmd.exe"
    $psi.Arguments = "/c cd /d `"$frontendPath`" && npm run dev"
    $psi.WorkingDirectory = $frontendPath
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    
    try {
        $process = [System.Diagnostics.Process]::Start($psi)
        $process.Id | Out-File -FilePath ".frontend.pid" -Encoding ASCII -NoNewline
        Write-Host "  Frontend process started (PID: $($process.Id))" -ForegroundColor Gray
    } catch {
        Write-Host "[X] Failed to start frontend: $_" -ForegroundColor Red
        return
    }
    
    Start-Sleep -Seconds 3
    Write-Host "[OK] Frontend running on http://localhost:$FRONTEND_PORT" -ForegroundColor Green
}

function Start-All {
    Print-Header
    
    # Check prerequisites quickly
    $pythonCmd = Get-PythonCommand
    if ($null -eq $pythonCmd -or -not (Test-Command "node")) {
        Write-Host "Prerequisites missing. Run: .\start.ps1 setup" -ForegroundColor Red
        exit 1
    }
    
    # Check Python deps
    try {
        $null = & $pythonCmd -c "import fastapi" 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw "FastAPI not found"
        }
    } catch {
        Write-Host "Python dependencies missing. Running setup..." -ForegroundColor Yellow
        Setup-System
    }
    
    if (-not (Test-Path "uploads")) { 
        New-Item -ItemType Directory -Path "uploads" -Force | Out-Null 
    }
    
    Stop-Services 2>$null
    Write-Host ""
    
    Start-Backend
    Start-Frontend
    
    Write-Host ""
    Write-Host "================================================================" -ForegroundColor Green
    Write-Host "  [OK] System Running!                                        " -ForegroundColor Green
    Write-Host "================================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Frontend:  http://localhost:$FRONTEND_PORT" -ForegroundColor Cyan
    Write-Host "  Backend:   http://localhost:$BACKEND_PORT" -ForegroundColor Cyan
    Write-Host "  API Docs:  http://localhost:$BACKEND_PORT/docs" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  Stop with: " -NoNewline
    Write-Host ".\start.ps1 stop" -ForegroundColor Yellow
    Write-Host ""
}

function Show-Status {
    Print-Header
    Write-Host "Service Status:" -ForegroundColor Cyan
    Write-Host ""
    
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$BACKEND_PORT/health" -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            Write-Host "  [OK] Backend:  http://localhost:$BACKEND_PORT (running)" -ForegroundColor Green
        } else {
            Write-Host "  [X] Backend:  not running" -ForegroundColor Red
        }
    } catch {
        Write-Host "  [X] Backend:  not running" -ForegroundColor Red
    }
    
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$FRONTEND_PORT" -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            Write-Host "  [OK] Frontend: http://localhost:$FRONTEND_PORT (running)" -ForegroundColor Green
        } else {
            Write-Host "  [X] Frontend: not running" -ForegroundColor Red
        }
    } catch {
        Write-Host "  [X] Frontend: not running" -ForegroundColor Red
    }
    Write-Host ""
}

function Show-Help {
    Print-Header
    Write-Host "Usage: .\start.ps1 <command>"
    Write-Host ""
    Write-Host "Commands:"
    Write-Host "  setup     Install all dependencies and configure the system"
    Write-Host "  start     Start backend and frontend servers"
    Write-Host "  stop      Stop all running services"
    Write-Host "  restart   Restart all services"
    Write-Host "  status    Check if services are running"
    Write-Host "  backend   Start only the backend server"
    Write-Host "  frontend  Start only the frontend server"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  .\start.ps1 setup    # First time setup"
    Write-Host "  .\start.ps1 start    # Start the application"
    Write-Host "  .\start.ps1 stop     # Stop all services"
    Write-Host ""
}

# Main
$command = if ($args.Count -gt 0) { $args[0] } else { "help" }

switch ($command.ToLower()) {
    "setup" {
        Setup-System
    }
    "start" {
        Start-All
    }
    "stop" {
        Stop-Services
    }
    "restart" {
        Stop-Services
        Start-Sleep -Seconds 2
        Start-All
    }
    "status" {
        Show-Status
    }
    "backend" {
        Start-Backend
    }
    "frontend" {
        Start-Frontend
    }
    default {
        Show-Help
    }
}
