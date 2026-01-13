const { app, BrowserWindow, screen } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const http = require('http');
const treeKill = require('tree-kill');

let mainWindow;
let apiProcess;
let nextProcess;
const API_PORT = 8000;
const NEXT_PORT = 3000;

const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged;

function getBackendPath() {
    if (isDev) {
        return { command: 'python', args: ['-m', 'uvicorn', 'backend.main:app', '--reload', '--port', String(API_PORT)] };
    } else {
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
        shell: isDev,
        env: { ...process.env, PORT: String(API_PORT) }
    });

    apiProcess.stdout.on('data', (data) => console.log(`Backend: ${data}`));
    apiProcess.stderr.on('data', (data) => console.error(`Backend Error: ${data}`));
    apiProcess.on('close', (code) => console.log(`Backend process exited with code ${code}`));
}

function startNextServer() {
    const cwd = isDev ? path.join(__dirname, '..') : process.resourcesPath;

    if (isDev) {
        // In dev, run next dev
        console.log('Starting Next.js dev server...');
        nextProcess = spawn('npm', ['run', 'dev'], {
            cwd: cwd,
            shell: true,
            env: { ...process.env, PORT: String(NEXT_PORT) }
        });
    } else {
        // In prod, run next start (requires .next folder to be packaged)
        console.log('Starting Next.js production server...');
        nextProcess = spawn('node', [path.join(cwd, 'node_modules/next/dist/bin/next'), 'start', '-p', String(NEXT_PORT)], {
            cwd: cwd,
            shell: process.platform === 'win32',
            env: { ...process.env }
        });
    }

    nextProcess.stdout.on('data', (data) => console.log(`Next.js: ${data}`));
    nextProcess.stderr.on('data', (data) => console.error(`Next.js Error: ${data}`));
    nextProcess.on('close', (code) => console.log(`Next.js process exited with code ${code}`));
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

    // Always load from Next.js server
    mainWindow.loadURL(`http://localhost:${NEXT_PORT}`);

    if (isDev) {
        mainWindow.webContents.openDevTools();
    }
}

function checkServerReady(port, name) {
    return new Promise((resolve, reject) => {
        const tryConnect = (retries = 30) => {
            http.get(`http://localhost:${port}`, (res) => {
                if (res.statusCode === 200 || res.statusCode === 404) resolve();
                else if (retries > 0) setTimeout(() => tryConnect(retries - 1), 1000);
                else reject(new Error(`${name} failed to start`));
            }).on('error', () => {
                if (retries > 0) setTimeout(() => tryConnect(retries - 1), 1000);
                else reject(new Error(`${name} connection refused`));
            });
        };
        tryConnect();
    });
}

app.whenReady().then(async () => {
    startBackend();
    startNextServer();

    try {
        console.log('Waiting for servers to start...');
        await Promise.all([
            checkServerReady(API_PORT, 'Backend'),
            checkServerReady(NEXT_PORT, 'Next.js')
        ]);
        console.log('All servers ready!');
        createWindow();
    } catch (err) {
        console.error('Failed to start servers:', err);
        createWindow(); // Open anyway to show error
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
    if (nextProcess) {
        treeKill(nextProcess.pid, 'SIGTERM', (err) => {
            if (err) console.error('Failed to kill Next.js process:', err);
        });
    }
});
