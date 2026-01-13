const { app, BrowserWindow, screen } = require('electron');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const http = require('http');
const treeKill = require('tree-kill');

let mainWindow;
let apiProcess;
let nextProcess;
const API_PORT = 8000;
const NEXT_PORT = 3000;

const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged;

function log(message) {
    console.log(`[${new Date().toISOString()}] ${message}`);
}

function getBackendPath() {
    if (isDev) {
        return {
            command: 'python',
            args: ['-m', 'uvicorn', 'backend.main:app', '--reload', '--port', String(API_PORT)],
            cwd: path.join(__dirname, '..')
        };
    } else {
        const executableName = process.platform === 'win32' ? 'api.exe' : 'api';
        const backendPath = path.join(process.resourcesPath, 'backend', executableName);
        log(`Backend path: ${backendPath}`);
        log(`Backend exists: ${fs.existsSync(backendPath)}`);
        return {
            command: backendPath,
            args: [],
            cwd: path.join(process.resourcesPath, 'backend')
        };
    }
}

function startBackend() {
    const { command, args, cwd } = getBackendPath();

    log(`Starting backend: ${command} ${args.join(' ')}`);
    log(`Backend CWD: ${cwd}`);

    try {
        apiProcess = spawn(command, args, {
            cwd: cwd,
            shell: isDev || process.platform === 'win32',
            env: { ...process.env, PORT: String(API_PORT) }
        });

        apiProcess.stdout.on('data', (data) => log(`Backend: ${data}`));
        apiProcess.stderr.on('data', (data) => log(`Backend: ${data}`));
        apiProcess.on('error', (err) => log(`Backend spawn error: ${err.message}`));
        apiProcess.on('close', (code) => log(`Backend process exited with code ${code}`));
    } catch (err) {
        log(`Failed to start backend: ${err.message}`);
    }
}

function startNextServer() {
    if (isDev) {
        const cwd = path.join(__dirname, '..');
        log('Starting Next.js dev server...');
        nextProcess = spawn('npm', ['run', 'dev'], {
            cwd: cwd,
            shell: true,
            env: { ...process.env, PORT: String(NEXT_PORT) }
        });
    } else {
        // In production, use the standalone server
        const nextjsDir = path.join(process.resourcesPath, 'nextjs');
        const serverPath = path.join(nextjsDir, 'server.js');

        log(`Next.js directory: ${nextjsDir}`);
        log(`Next.js dir exists: ${fs.existsSync(nextjsDir)}`);
        log(`Server.js path: ${serverPath}`);
        log(`Server.js exists: ${fs.existsSync(serverPath)}`);

        // List directory contents for debugging
        try {
            if (fs.existsSync(nextjsDir)) {
                const contents = fs.readdirSync(nextjsDir);
                log(`Next.js dir contents: ${contents.join(', ')}`);
            }
        } catch (err) {
            log(`Error listing directory: ${err.message}`);
        }

        if (!fs.existsSync(serverPath)) {
            log('ERROR: server.js not found!');
            return;
        }

        log('Starting Next.js standalone server...');
        nextProcess = spawn('node', [serverPath], {
            cwd: nextjsDir,
            shell: process.platform === 'win32',
            env: {
                ...process.env,
                PORT: String(NEXT_PORT),
                HOSTNAME: '0.0.0.0'
            }
        });
    }

    nextProcess.stdout.on('data', (data) => log(`Next.js: ${data}`));
    nextProcess.stderr.on('data', (data) => log(`Next.js: ${data}`));
    nextProcess.on('error', (err) => log(`Next.js spawn error: ${err.message}`));
    nextProcess.on('close', (code) => log(`Next.js process exited with code ${code}`));
}

function createWindow(errorMessage = null) {
    const { width, height } = screen.getPrimaryDisplay().workAreaSize;

    mainWindow = new BrowserWindow({
        width: Math.min(1440, width),
        height: Math.min(900, height),
        icon: path.join(__dirname, 'resources', 'icon.png'),
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            nodeIntegration: false,
            contextIsolation: true
        },
    });

    if (errorMessage) {
        mainWindow.loadURL(`data:text/html,
      <html>
        <head><title>Error - OCR Form Extractor</title></head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, sans-serif; padding: 40px; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); color: white; min-height: 100vh; margin: 0;">
          <h1 style="color: #e94560;">Failed to Start</h1>
          <p style="font-size: 18px;">${errorMessage}</p>
          <p style="color: #888; margin-top: 30px;">Please check the application logs for more details.</p>
        </body>
      </html>
    `);
    } else {
        // Load from Next.js server
        mainWindow.loadURL(`http://localhost:${NEXT_PORT}`);
    }

    if (isDev) {
        mainWindow.webContents.openDevTools();
    }
}

function checkServerReady(port, name) {
    return new Promise((resolve, reject) => {
        const tryConnect = (retries = 90) => {
            log(`Checking ${name} on port ${port} (${retries} retries left)`);
            http.get(`http://localhost:${port}`, (res) => {
                log(`${name} responded with status ${res.statusCode}`);
                if (res.statusCode === 200 || res.statusCode === 404 || res.statusCode === 302) resolve();
                else if (retries > 0) setTimeout(() => tryConnect(retries - 1), 500);
                else reject(new Error(`${name} failed - status ${res.statusCode}`));
            }).on('error', (err) => {
                if (retries > 0) setTimeout(() => tryConnect(retries - 1), 500);
                else reject(new Error(`${name} connection refused after 45s`));
            });
        };
        tryConnect();
    });
}

app.whenReady().then(async () => {
    log('App ready, starting servers...');
    log(`isDev: ${isDev}`);
    if (!isDev) {
        log(`resourcesPath: ${process.resourcesPath}`);
        try {
            const contents = fs.readdirSync(process.resourcesPath);
            log(`Resources contents: ${contents.join(', ')}`);
        } catch (err) {
            log(`Error listing resources: ${err.message}`);
        }
    }

    startBackend();
    startNextServer();

    try {
        log('Waiting for servers to start...');
        await Promise.all([
            checkServerReady(API_PORT, 'Backend'),
            checkServerReady(NEXT_PORT, 'Next.js')
        ]);
        log('All servers ready! Opening window...');
        createWindow();
    } catch (err) {
        log(`Failed to start servers: ${err.message}`);
        createWindow(err.message);
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
        log('Killing backend process...');
        treeKill(apiProcess.pid, 'SIGTERM', (err) => {
            if (err) log(`Failed to kill backend: ${err}`);
        });
    }
    if (nextProcess) {
        log('Killing Next.js process...');
        treeKill(nextProcess.pid, 'SIGTERM', (err) => {
            if (err) log(`Failed to kill Next.js: ${err}`);
        });
    }
});
