# Building Desktop Executables

This guide explains how to build native desktop applications (.exe, .dmg, .AppImage) for the OCR Admission Forms system.

## Quick Build

```bash
# Build for your current platform
npm run desktop:build

# Build for specific platforms
npm run desktop:build:win    # Windows (.exe)
npm run desktop:build:mac    # macOS (.dmg)
npm run desktop:build:linux  # Linux (.AppImage, .deb, .rpm)
```

## Prerequisites

### All Platforms
- Node.js 18 or later
- Python 3.8 or later
- npm (comes with Node.js)

### Windows
```powershell
# Install Python from python.org
# Install Node.js from nodejs.org
# Install Visual Studio Build Tools (for native modules)
npm install -g windows-build-tools
```

### macOS
```bash
# Install Xcode Command Line Tools
xcode-select --install

# Install Node.js via Homebrew
brew install node python@3.11
```

### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install -y nodejs npm python3 python3-pip python3-venv \
    build-essential libfuse2 rpm
```

## Step-by-Step Build Process

### 1. Install Dependencies

```bash
# Clone and enter project
cd OCR-admission-forms

# Install Node.js dependencies
npm install

# Install desktop app dependencies
npm run desktop:install

# Install Python dependencies
pip install -r requirements.txt
pip install pyinstaller
```

### 2. Build Python Backend

The Python backend must be bundled into a standalone executable:

```bash
cd desktop

# macOS/Linux
./build-python.sh

# Windows
build-python.bat
```

This creates `desktop/dist/python/ocr-backend` (or `.exe` on Windows).

### 3. Build Next.js Frontend

```bash
cd ..  # back to project root
npm run build
```

### 4. Build Desktop App

```bash
cd desktop
npm run build:electron
```

Or build for a specific platform:
```bash
npm run build:win     # Windows
npm run build:mac     # macOS
npm run build:linux   # Linux
```

### 5. Find Your Installer

Built installers are in `desktop/release/`:

| Platform | Filename |
|----------|----------|
| Windows | `OCR Admission Forms-Setup-1.0.0.exe` |
| macOS (Intel) | `OCR Admission Forms-1.0.0-x64.dmg` |
| macOS (Apple Silicon) | `OCR Admission Forms-1.0.0-arm64.dmg` |
| Linux | `OCR Admission Forms-1.0.0.AppImage` |

## Build Size

Expected installer sizes:

| Component | Size |
|-----------|------|
| Electron runtime | ~150 MB |
| Python backend + dependencies | ~800 MB |
| OCR models | ~200 MB |
| Next.js frontend | ~50 MB |
| **Total installer** | **~1.2 GB** |

## Reducing Build Size

To create a smaller build:

1. **Use Tesseract-only OCR** (skip PyTorch):
   Edit `pyinstaller.spec` to exclude torch/transformers

2. **Download models on first run**:
   Instead of bundling models, download them when the app starts

3. **Use UPX compression**:
   Already enabled in electron-builder.yml

## Code Signing (Production)

### Windows
1. Obtain a code signing certificate
2. Set environment variables:
   ```bash
   export CSC_LINK=path/to/certificate.pfx
   export CSC_KEY_PASSWORD=your_password
   ```

### macOS
1. Enroll in Apple Developer Program
2. Create signing certificates in Xcode
3. Set up notarization:
   ```bash
   export APPLE_ID=your@email.com
   export APPLE_ID_PASSWORD=app-specific-password
   export APPLE_TEAM_ID=your_team_id
   ```

## CI/CD Build (GitHub Actions)

Create `.github/workflows/build-desktop.yml`:

```yaml
name: Build Desktop App

on:
  release:
    types: [created]

jobs:
  build:
    strategy:
      matrix:
        os: [windows-latest, macos-latest, ubuntu-latest]
    
    runs-on: ${{ matrix.os }}
    
    steps:
      - uses: actions/checkout@v4
      
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          npm install
          npm run desktop:install
          pip install -r requirements.txt
          pip install pyinstaller
      
      - name: Build
        run: npm run desktop:build
      
      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: desktop-${{ matrix.os }}
          path: desktop/release/*
```

## Troubleshooting

### "Python not found" error
```bash
# Ensure Python is in PATH
python --version
# or
python3 --version
```

### PyInstaller fails
```bash
# Clean and retry
cd desktop
rm -rf build dist
pip install --upgrade pyinstaller
./build-python.sh
```

### Electron build fails
```bash
# Clear cache and rebuild
cd desktop
rm -rf release node_modules
npm install
npm run build:electron
```

### macOS: "App is damaged"
This happens with unsigned apps. Either:
1. Sign the app with a Developer ID
2. Run: `xattr -cr "/Applications/OCR Admission Forms.app"`

### Linux: AppImage won't run
```bash
chmod +x "OCR Admission Forms-1.0.0.AppImage"
# Install FUSE if needed
sudo apt install libfuse2
```

## Testing the Build

After building, test on a clean machine:

1. Install the app
2. Launch - should show splash screen
3. Wait for backend to start (~10-30 seconds first time)
4. Upload a test form
5. Verify OCR extraction works
6. Check that data persists after restart

## Support

For build issues, check:
- `desktop/release/*.log` - Build logs
- App logs in user data folder
- GitHub Issues for known problems
