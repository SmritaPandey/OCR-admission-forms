const { app, BrowserWindow, screen, dialog } = require('electron');
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

// Logging helper
function log(message) {
    console.log(`[${new Date().toISOString()}] ${message}`);
}

function getBackendPath() {
    if (isDev) {
        return { command: 'python', args: ['-m', 'uvicorn', 'backend.main:app', '--reload', '--port', String(API_PORT)] };
    } else {
        const executableName = process.platform === 'win32' ? 'api.exe' : 'api';
        const backendPath = path.join(process.resourcesPath, 'backend', executableName);
        log(`Backend path: ${backendPath}`);
        log(`Backend exists: ${fs.existsSync(backendPath)}`);
        return {
            command: backendPath,
            args: []
        };
    }
}

function startBackend() {
    const { command, args } = getBackendPath();
    const cwd = isDev ? path.join(__dirname, '..') : path.join(process.resourcesPath, 'backend');

    log(`Starting backend: ${command} ${args.join(' ')}`);
    log(`Backend CWD: ${cwd}`);

    try {
        apiProcess = spawn(command, args, {
            cwd: cwd,
            shell: isDev,
            env: { ...process.env, PORT: String(API_PORT) }
        });

        apiProcess.stdout.on('data', (data) => log(`Backend: ${data}`));
        apiProcess.stderr.on('data', (data) => log(`Backend Error: ${data}`));
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
        // In prod, use the standalone server created by Next.js
        const standaloneDir = path.join(process.resourcesPath, 'standalone');
        const serverPath = path.join(standaloneDir, 'server.js');

        log(`Standalone dir: ${standaloneDir}`);
        log(`Standalone dir exists: ${fs.existsSync(standaloneDir)}`);
        log(`Server.js path: ${serverPath}`);
        log(`Server.js exists: ${fs.existsSync(serverPath)}`);

        // List contents of resourcesPath for debugging
        try {
            const resourcesContents = fs.readdirSync(process.resourcesPath);
            log(`Resources contents: ${resourcesContents.join(', ')}`);

            if (fs.existsSync(standaloneDir)) {
                const standaloneContents = fs.readdirSync(standaloneDir);
                log(`Standalone contents: ${standaloneContents.join(', ')}`);
            }
        } catch (err) {
            log(`Error listing directories: ${err.message}`);
        }

        if (!fs.existsSync(serverPath)) {
            log('ERROR: server.js not found! Check build configuration.');
            return;
        }

        log(`Starting Next.js standalone server from: ${serverPath}`);

        try {
            nextProcess = spawn('node', [serverPath], {
                cwd: standaloneDir,
                shell: process.platform === 'win32',
                env: {
                    ...process.env,
                    PORT: String(NEXT_PORT),
                    HOSTNAME: '0.0.0.0'
                }
            });

            nextProcess.stdout.on('data', (data) => log(`Next.js: ${data}`));
            nextProcess.stderr.on('data', (data) => log(`Next.js Error: ${data}`));
            nextProcess.on('error', (err) => log(`Next.js spawn error: ${err.message}`));
            nextProcess.on('close', (code) => log(`Next.js process exited with code ${code}`));
        } catch (err) {
            log(`Failed to start Next.js: ${err.message}`);
        }
    }
}

function createWindow(errorMessage = null) {
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

    if (errorMessage) {
        // Show error page
        mainWindow.loadURL(`data:text/html,
      <html>
        <head><title>Error</title></head>
        <body style="font-family: sans-serif; padding: 40px; background: #1a1a2e; color: white;">
          <h1 style="color: #e94560;">Failed to Start</h1>
          <p>${errorMessage}</p>
          <pre style="background: #16213e; padding: 20px; border-radius: 8px; overflow: auto;">${errorMessage}</pre>
          <p>Check the logs for more details.</p>
        </body>
      </html>
    `);
    } else {
        mainWindow.loadURL(`http://localhost:${NEXT_PORT}`);
    }

    if (isDev) {
        mainWindow.webContents.openDevTools();
    }
}

function checkServerReady(port, name) {
    return new Promise((resolve, reject) => {
        const tryConnect = (retries = 60) => {
            log(`Checking ${name} on port ${port} (${retries} retries left)`);
            http.get(`http://localhost:${port}`, (res) => {
                log(`${name} responded with status ${res.statusCode}`);
                if (res.statusCode === 200 || res.statusCode === 404 || res.statusCode === 302) resolve();
                else if (retries > 0) setTimeout(() => tryConnect(retries - 1), 500);
                else reject(new Error(`${name} failed to start - got status ${res.statusCode}`));
            }).on('error', (err) => {
                if (retries > 0) setTimeout(() => tryConnect(retries - 1), 500);
                else reject(new Error(`${name} connection refused: ${err.message}`));
            });
        };
        tryConnect();
    });
}

app.whenReady().then(async () => {
    log('App ready, starting servers...');
    log(`isDev: ${isDev}`);
    log(`resourcesPath: ${process.resourcesPath}`);

    startBackend();
    startNextServer();

    try {
        log('Waiting for servers to start...');
        await Promise.all([
            checkServerReady(API_PORT, 'Backend'),
            checkServerReady(NEXT_PORT, 'Next.js')
        ]);
        log('All servers ready!');
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
        treeKill(apiProcess.pid, 'SIGTERM', (err) => {
            if (err) log(`Failed to kill backend process: ${err}`);
        });
    }
    if (nextProcess) {
        treeKill(nextProcess.pid, 'SIGTERM', (err) => {
            if (err) log(`Failed to kill Next.js process: ${err}`);
        });
    }
});
