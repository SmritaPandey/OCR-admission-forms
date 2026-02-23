# 🚀 Quick Deployment Guide

This guide helps you deploy the Student Admission Form OCR System on a new laptop in minutes.

## Prerequisites

### Required Software
- **Python 3.8+** with pip
- **Node.js 18+** with npm
- **Git** (to clone the repository)

### Optional (Recommended)
- **Docker & Docker Compose** (for containerized deployment)
- **Tesseract OCR** (for free local OCR)

---

## Option 1: Quick Start with Make (Recommended)

```bash
# 1. Clone the repository
git clone <repository-url>
cd OCR-admission-forms

# 2. Run setup (installs all dependencies)
make setup

# 3. Start the application
make dev
```

**Access the application:**
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## Option 2: Docker Deployment (Easiest)

```bash
# 1. Clone the repository
git clone <repository-url>
cd OCR-admission-forms

# 2. Copy environment file
cp .env.example .env

# 3. Build and start with Docker
docker-compose up -d --build

# Or use Make:
make docker-up
```

**Access the application:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000

**Stop the application:**
```bash
docker-compose down
# Or: make docker-down
```

---

## Option 3: Manual Setup (Linux/macOS)

```bash
# 1. Clone the repository
git clone <repository-url>
cd OCR-admission-forms

# 2. Create and activate Python virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Install Node.js dependencies
npm install
cd frontend && npm install && cd ..

# 5. Copy environment configuration
cp .env.example .env

# 6. Create required directories
mkdir -p uploads training_data

# 7. Start backend (in one terminal)
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# 8. Start frontend (in another terminal)
npm run dev
```

---

## Option 4: Using the Start Script

```bash
# First time setup
./start.sh setup

# Start the application
./start.sh start

# Stop the application
./start.sh stop

# Check status
./start.sh status
```

---

## Platform-Specific Installation

### macOS

```bash
# Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install prerequisites
brew install python@3.11 node tesseract

# Verify installations
python3 --version
node --version
tesseract --version
```

### Ubuntu/Debian Linux

```bash
# Update package manager
sudo apt update

# Install prerequisites
sudo apt install -y python3 python3-pip python3-venv nodejs npm tesseract-ocr

# Verify installations
python3 --version
node --version
tesseract --version
```

### Windows

1. **Python**: Download from https://python.org (check "Add to PATH")
2. **Node.js**: Download from https://nodejs.org
3. **Tesseract**: Download from https://github.com/UB-Mannheim/tesseract/wiki
4. **Git**: Download from https://git-scm.com

Then use PowerShell or Git Bash:
```powershell
# Clone and setup
git clone <repository-url>
cd OCR-admission-forms
pip install -r requirements.txt
npm install
cd frontend && npm install && cd ..

# Start backend
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Start frontend (new terminal)
npm run dev
```

---

## Configuration

### Minimal Configuration (Works out of the box)

The default configuration uses:
- **SQLite** database (no setup required)
- **Tesseract** OCR (free, local)

Just copy `.env.example` to `.env` and you're ready!

### Recommended Configuration (Better OCR)

For better handwriting recognition, enable cloud OCR providers:

```env
# .env file

# Enable Google Vision for better accuracy
OCR_PROVIDER=google-vision
OCR_ENABLE_GOOGLE_VISION=true
GOOGLE_APPLICATION_CREDENTIALS=path/to/your/credentials.json
```

### Available OCR Providers

| Provider | Accuracy | Cost | Setup |
|----------|----------|------|-------|
| Tesseract | ⭐⭐⭐ | Free | Easy |
| Google Vision | ⭐⭐⭐⭐ | $$ | Medium |
| CRAFT+TrOCR | ⭐⭐⭐⭐⭐ | Free | Medium |
| Claude Vision | ⭐⭐⭐⭐⭐ | $$$ | Easy |
| Azure Form Recognizer | ⭐⭐⭐⭐⭐ | $$ | Medium |

---

## Make Commands Reference

```bash
make help          # Show all available commands

# Development
make install       # Install all dependencies
make setup         # Full setup (install + db + directories)
make dev           # Start both servers in dev mode
make backend       # Start only backend
make frontend      # Start only frontend (Next.js)
make stop          # Stop all services

# Docker
make docker-build  # Build Docker images
make docker-up     # Start Docker containers
make docker-down   # Stop Docker containers
make docker-logs   # View container logs

# Utilities
make clean         # Clean build artifacts
make db-backup     # Backup SQLite database
make db-reset      # Reset database
```

---

## Troubleshooting

### Backend won't start

```bash
# Check Python version
python3 --version  # Should be 3.8+

# Reinstall dependencies
pip install -r requirements.txt --upgrade

# Check for port conflicts
lsof -i :8000
```

### Frontend won't start

```bash
# Check Node version
node --version  # Should be 18+

# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
```

### OCR not working

```bash
# Check Tesseract installation
tesseract --version

# macOS
brew install tesseract

# Ubuntu/Debian
sudo apt install tesseract-ocr
```

### Docker issues

```bash
# Rebuild images
docker-compose build --no-cache

# Check logs
docker-compose logs -f

# Reset everything
docker-compose down -v
docker-compose up -d --build
```

---

## Quick Verification

After starting the application:

1. **Check Backend Health:**
   ```bash
   curl http://localhost:8000/health
   # Should return: {"status":"healthy"}
   ```

2. **Open Frontend:**
   - Navigate to http://localhost:3000 (Docker) or http://localhost:5173 (local)

3. **Test Upload:**
   - Go to the Upload page
   - Upload a sample form from `data/samples/`
   - Verify OCR extraction works

---

## Next Steps

1. **Configure OCR**: Edit `.env` to enable your preferred OCR provider
2. **Upload Forms**: Start uploading and processing admission forms
3. **Train Models**: Use the Training page to improve OCR accuracy
4. **Export Data**: Export verified forms to CSV/JSON

For detailed documentation, see:
- `README.md` - Full documentation
- `SETUP_OCR.md` - OCR provider setup
- `USE_CRAFT_TROCR.md` - Training custom models

---

**Need help?** Check the logs:
```bash
# Local
tail -f backend.log

# Docker
docker-compose logs -f backend
```
