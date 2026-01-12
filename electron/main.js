const { app, BrowserWindow, screen } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const http = require('http');
const treeKill = require('tree-kill');

let mainWindow;
let apiProcess;
const API_PORT = 8000;

// Determine environment
const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged;

function getBackendPath() {
    if (isDev) {
        // In dev, assume venv is active or python is accessible
        // For simplicity in dev, we might assume the user runs the backend manually?
        // OR we strive to spawn it. Let's try to spawn it relative to project root.
        return { command: 'python', args: ['-m', 'uvicorn', 'backend.main:app', '--reload', '--port', '8000'] };
    } else {
        // In production, the backend is an executable in resources/backend
        // Windows: api.exe, Mac/Linux: api
        const executableName = process.platform === 'win32' ? 'api.exe' : 'api';
        return {
            command: path.join(process.resourcesPath, 'backend', executableName),
            args: []
        };
    }
}

function startBackend() {
    const { command, args } = getBackendPath();
    const cwd = isDev ? path.join(__dirname, '..') : path.join(process.resourcesPath, 'backend');

    console.log(`Starting backend: ${command} ${args.join(' ')}`);

    apiProcess = spawn(command, args, {
        cwd: cwd,
        shell: isDev, // Needed for python in dev usually
        env: { ...process.env, PORT: API_PORT.toString() }
    });

    apiProcess.stdout.on('data', (data) => console.log(`Backend: ${data}`));
    apiProcess.stderr.on('data', (data) => console.error(`Backend Error: ${data}`));

    apiProcess.on('close', (code) => {
        console.log(`Backend process exited with code ${code}`);
    });
}

function createWindow() {
    const { width, height } = screen.getPrimaryDisplay().workAreaSize;

    mainWindow = new BrowserWindow({
        width: Math.min(1440, width),
        height: Math.min(900, height),
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            nodeIntegration: false,
            contextIsolation: true
        },
    });

    // Load Frontend
    if (isDev) {
        // In dev, assume Next.js is running on 3000
        mainWindow.loadURL('http://localhost:3000');
        mainWindow.webContents.openDevTools();
    } else {
        // In prod, load from static export
        const startUrl = path.join(process.resourcesPath, 'frontend', 'index.html');
        mainWindow.loadFile(startUrl);
    }
}

// Check if backend is ready
function checkBackendReady() {
    return new Promise((resolve, reject) => {
        const tryConnect = (retries = 20) => {
            http.get(`http://localhost:${API_PORT}/docs`, (res) => {
                if (res.statusCode === 200) resolve();
                else if (retries > 0) setTimeout(() => tryConnect(retries - 1), 1000);
                else reject(new Error('Backend failed to start'));
            }).on('error', () => {
                if (retries > 0) setTimeout(() => tryConnect(retries - 1), 1000);
                else reject(new Error('Backend connection refused'));
            });
        };
        tryConnect();
    });
}

app.whenReady().then(async () => {
    startBackend();
    try {
        await checkBackendReady();
        createWindow();
    } catch (err) {
        console.error('Failed to start backend:', err);
        // Open window anyway to show error? or dialog?
        // For now, crash or show simpler window
        createWindow();
    }

    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) createWindow();
    });
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') app.quit();
});

app.on('will-quit', () => {
    if (apiProcess) {
        treeKill(apiProcess.pid, 'SIGTERM', (err) => {
            if (err) console.error('Failed to kill backend process:', err);
        });
    }
});
