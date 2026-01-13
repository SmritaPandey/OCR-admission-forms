const { app, BrowserWindow, screen } = require('electron');
const path = require('path');
const fs = require('fs');
const { spawn, execFile } = require('child_process');
const http = require('http');
const treeKill = require('tree-kill');

let mainWindow;
let apiProcess;
let viteProcess;
const API_PORT = 8000;
const VITE_PORT = 5173;

const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged;

function log(message) {
    const timestamp = new Date().toISOString();
    console.log(`[${timestamp}] ${message}`);
    // Also write to a log file for debugging
    if (!isDev) {
        const logPath = path.join(app.getPath('userData'), 'app.log');
        try {
            fs.appendFileSync(logPath, `[${timestamp}] ${message}\n`);
        } catch (e) {
            // Ignore log file errors
        }
    }
}

function getBackendPath() {
    if (isDev) {
        return {
            command: 'python',
            args: ['-m', 'uvicorn', 'backend.main:app', '--host', '127.0.0.1', '--port', String(API_PORT)],
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

    // Set desktop app environment
    // Use AppData for writable files (not Program Files which is read-only)
    const userDataPath = app.getPath('userData');  // Returns AppData/Roaming/OCR Form Extractor
    const dataDir = path.join(userDataPath, 'data');

    // Ensure data directory exists
    try {
        if (!fs.existsSync(dataDir)) {
            fs.mkdirSync(dataDir, { recursive: true });
        }
        // Copy config files from resources to AppData if they don't exist
        const resourcesDataDir = path.join(process.resourcesPath, 'data');
        const filesToCopy = ['.env', 'google-cloud-credentials.json', 'admission_forms.db'];
        for (const file of filesToCopy) {
            const srcPath = path.join(resourcesDataDir, file);
            const destPath = path.join(dataDir, file);
            if (fs.existsSync(srcPath) && !fs.existsSync(destPath)) {
                fs.copyFileSync(srcPath, destPath);
                log(`Copied ${file} to AppData`);
            }
        }
    } catch (err) {
        log(`Warning: Could not setup data directory: ${err.message}`);
    }

    const backendEnv = {
        ...process.env,
        PORT: String(API_PORT),
        HOST: '127.0.0.1',
        DESKTOP_APP: '1',  // Signal to backend that it's running in desktop mode
        DATA_DIR: dataDir  // Use AppData instead of Program Files
    };

    try {
        // On Windows, paths with spaces need special handling
        // Use execFile for better path handling, or properly quote for shell
        if (process.platform === 'win32' && !isDev) {
            // For Windows production, use execFile which handles paths with spaces better
            log(`Spawning backend with execFile: ${command}`);
            log(`Backend ENV - DATA_DIR: ${backendEnv.DATA_DIR}`);
            log(`Backend ENV - DESKTOP_APP: ${backendEnv.DESKTOP_APP}`);

            apiProcess = execFile(command, args, {
                cwd: cwd,
                env: backendEnv
            });
        } else {
            // For dev mode or non-Windows, use spawn
            const spawnOptions = {
                cwd: cwd,
                env: backendEnv,
                shell: isDev || process.platform === 'win32'
            };
            log(`Spawning backend with spawn: ${command} ${args.join(' ')}`);
            log(`Backend ENV - DATA_DIR: ${backendEnv.DATA_DIR}`);
            log(`Backend ENV - DESKTOP_APP: ${backendEnv.DESKTOP_APP}`);

            apiProcess = spawn(command, args, spawnOptions);
        }

        let backendOutput = '';
        apiProcess.stdout.on('data', (data) => {
            const output = data.toString();
            backendOutput += output;
            log(`Backend: ${output}`);
        });
        apiProcess.stderr.on('data', (data) => {
            const output = data.toString();
            backendOutput += output;
            log(`Backend ERROR: ${output}`);
        });
        apiProcess.on('error', (err) => {
            log(`Backend spawn error: ${err.message}`);
            createWindow(`Failed to start backend: ${err.message}`);
        });
        apiProcess.on('close', (code) => {
            log(`Backend process exited with code ${code}`);
            if (code !== 0 && code !== null) {
                createWindow(`Backend exited with code ${code}. Last output: ${backendOutput.slice(-500)}`);
            }
        });
    } catch (err) {
        log(`Failed to start backend: ${err.message}`);
        createWindow(`Failed to start backend: ${err.message}`);
    }
}

function startViteServer() {
    if (isDev) {
        const cwd = path.join(__dirname, '..', 'frontend');
        log('Starting Vite dev server...');
        viteProcess = spawn('npm', ['run', 'dev'], {
            cwd: cwd,
            shell: true,
            env: {
                ...process.env,
                PORT: String(VITE_PORT),
                VITE_API_BASE_URL: `http://127.0.0.1:${API_PORT}`
            }
        });
        viteProcess.stdout.on('data', (data) => log(`Vite: ${data}`));
        viteProcess.stderr.on('data', (data) => log(`Vite: ${data}`));
        viteProcess.on('error', (err) => log(`Vite spawn error: ${err.message}`));
        viteProcess.on('close', (code) => log(`Vite process exited with code ${code}`));
    }
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
            contextIsolation: true,
            webSecurity: false  // Allow local file access in production
        },
    });

    // Show window immediately even if loading
    mainWindow.show();

    if (errorMessage) {
        const errorHtml = `<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Error - OCR Form Extractor</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            padding: 40px;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: white;
            min-height: 100vh;
            margin: 0;
        }
        h1 { color: #e94560; margin-top: 0; }
        pre {
            background: rgba(0,0,0,0.3);
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            white-space: pre-wrap;
            word-wrap: break-word;
        }
        .info { color: #888; margin-top: 20px; }
        button {
            background: #e94560;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            margin-top: 20px;
        }
        button:hover { background: #d63447; }
    </style>
</head>
<body>
    <h1>Failed to Start</h1>
    <pre>${errorMessage.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</pre>
    <p class="info">Please check the application logs for more details.</p>
    <p class="info">Log file location: ${app.getPath('userData')}\\app.log</p>
    <button onclick="location.reload()">Retry</button>
</body>
</html>`;
        mainWindow.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(errorHtml)}`);

        // Always show DevTools for errors
        mainWindow.webContents.openDevTools();
    } else {
        if (isDev) {
            // In development, load from Vite dev server
            mainWindow.loadURL(`http://127.0.0.1:${VITE_PORT}`);
        } else {
            // In production, load from bundled frontend
            const frontendPath = path.join(process.resourcesPath, 'frontend', 'index.html');
            log(`Attempting to load frontend from: ${frontendPath}`);
            log(`Frontend exists: ${fs.existsSync(frontendPath)}`);

            if (fs.existsSync(frontendPath)) {
                // Use file:// protocol for local files
                mainWindow.loadFile(frontendPath).catch(err => {
                    log(`Failed to load frontend file: ${err.message}`);
                    createWindow(`Failed to load frontend: ${err.message}`);
                });
            } else {
                log(`ERROR: Frontend not found at ${frontendPath}`);
                // List what's actually in the resources directory
                try {
                    const resourcesContents = fs.readdirSync(process.resourcesPath);
                    log(`Resources directory contents: ${resourcesContents.join(', ')}`);
                } catch (e) {
                    log(`Could not list resources: ${e.message}`);
                }
                mainWindow.loadURL(`data:text/html,
          <html>
            <head><title>Error - OCR Form Extractor</title></head>
            <body style="font-family: -apple-system, BlinkMacSystemFont, sans-serif; padding: 40px; background: #f5f5f5;">
              <h1 style="color: #e94560;">Frontend Not Found</h1>
              <p>Frontend files not found at:</p>
              <pre style="background: #fff; padding: 10px; border-radius: 4px;">${frontendPath}</pre>
              <p style="margin-top: 20px;">Resources path: ${process.resourcesPath}</p>
            </body>
          </html>
        `);
            }
        }
    }

    // Open DevTools in dev mode, or if SHOW_DEVTOOLS env var is set
    if (isDev || process.env.SHOW_DEVTOOLS === '1') {
        mainWindow.webContents.openDevTools();
    }

    // Add keyboard shortcut to toggle DevTools (Ctrl+Shift+I)
    mainWindow.webContents.on('before-input-event', (event, input) => {
        if (input.control && input.shift && input.key.toLowerCase() === 'i') {
            mainWindow.webContents.toggleDevTools();
        }
    });
}

function checkServerReady(port, name) {
    return new Promise((resolve, reject) => {
        const tryConnect = (retries = 90) => {
            log(`Checking ${name} on port ${port} (${retries} retries left)`);
            http.get(`http://127.0.0.1:${port}`, (res) => {
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
    if (isDev) {
        startViteServer();
    }

    try {
        log('Waiting for backend to start...');
        await checkServerReady(API_PORT, 'Backend');

        if (isDev) {
            log('Waiting for Vite dev server to start...');
            await checkServerReady(VITE_PORT, 'Vite');
        }

        log('All servers ready! Opening window...');
        createWindow();
    } catch (err) {
        log(`Failed to start servers: ${err.message}`);
        const errorMsg = `Failed to start backend server: ${err.message}\n\nPlease check:\n1. Port ${API_PORT} is not in use\n2. Backend executable exists\n3. Configuration files are present`;
        createWindow(errorMsg);
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
    if (viteProcess) {
        log('Killing Vite process...');
        treeKill(viteProcess.pid, 'SIGTERM', (err) => {
            if (err) log(`Failed to kill Vite: ${err}`);
        });
    }
});
