const { contextBridge, ipcRenderer, shell } = require('electron');

// Expose API base URL for frontend
contextBridge.exposeInMainWorld('electronAPI', {
    openExternal: (url) => shell.openExternal(url),
    send: (channel, data) => {
        // whitelist channels
        let validChannels = ['toMain'];
        if (validChannels.includes(channel)) {
            ipcRenderer.send(channel, data);
        }
    },
    receive: (channel, func) => {
        let validChannels = ['fromMain'];
        if (validChannels.includes(channel)) {
            // Deliberately strip event as it includes `sender` 
            ipcRenderer.on(channel, (event, ...args) => func(...args));
        }
    },
    // Expose API URL for frontend
    getApiBaseUrl: () => 'http://localhost:8000'
});

// Inject API base URL into window for frontend
if (typeof window !== 'undefined') {
    window.API_BASE_URL = 'http://localhost:8000';
}