#!/bin/bash
# =============================================================================
# Student Admission Form OCR System - Cross-Platform Setup Script
# =============================================================================
# This script sets up the complete development environment on a new machine.
# Supports: macOS, Linux (Ubuntu/Debian/RHEL/Fedora), and provides guidance for Windows
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Project directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

print_header() {
    echo -e "${CYAN}"
    echo "╔════════════════════════════════════════════════════════════════════╗"
    echo "║     Student Admission Form OCR System - Setup Script               ║"
    echo "╚════════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_step() {
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}▶ $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Detect operating system
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
    elif [[ -f /etc/debian_version ]]; then
        OS="debian"
    elif [[ -f /etc/redhat-release ]]; then
        OS="redhat"
    elif [[ -f /etc/fedora-release ]]; then
        OS="fedora"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        OS="windows"
    else
        OS="unknown"
    fi
    echo "$OS"
}

# Check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Install system dependencies
install_system_deps() {
    print_step "Installing System Dependencies"
    
    local OS=$(detect_os)
    
    case $OS in
        macos)
            echo "Detected: macOS"
            if ! command_exists brew; then
                print_warning "Homebrew not found. Installing..."
                /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
            fi
            
            echo "Installing dependencies via Homebrew..."
            brew install python@3.11 node tesseract || true
            ;;
            
        debian)
            echo "Detected: Debian/Ubuntu"
            sudo apt-get update
            sudo apt-get install -y \
                python3 python3-pip python3-venv \
                nodejs npm \
                tesseract-ocr tesseract-ocr-eng \
                libpq-dev gcc g++ \
                libjpeg-dev zlib1g-dev libpng-dev libtiff-dev \
                curl git
            ;;
            
        redhat|fedora)
            echo "Detected: RHEL/Fedora"
            sudo dnf install -y \
                python3 python3-pip python3-virtualenv \
                nodejs npm \
                tesseract tesseract-langpack-eng \
                postgresql-devel gcc gcc-c++ \
                libjpeg-devel zlib-devel libpng-devel libtiff-devel \
                curl git
            ;;
            
        windows)
            echo "Detected: Windows (Git Bash/Cygwin)"
            print_warning "Please install the following manually:"
            echo "  1. Python 3.11+: https://python.org"
            echo "  2. Node.js 18+:  https://nodejs.org"
            echo "  3. Tesseract:    https://github.com/UB-Mannheim/tesseract/wiki"
            echo ""
            echo "After installing, run this script again."
            ;;
            
        *)
            print_warning "Unknown OS. Please install manually:"
            echo "  - Python 3.8+"
            echo "  - Node.js 18+"
            echo "  - Tesseract OCR (optional)"
            ;;
    esac
}

# Check prerequisites
check_prerequisites() {
    print_step "Checking Prerequisites"
    
    local all_ok=true
    
    # Python
    if command_exists python3; then
        PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
        print_success "Python: $PYTHON_VERSION"
    else
        print_error "Python 3 not found"
        all_ok=false
    fi
    
    # Node.js
    if command_exists node; then
        NODE_VERSION=$(node --version)
        print_success "Node.js: $NODE_VERSION"
    else
        print_error "Node.js not found"
        all_ok=false
    fi
    
    # npm
    if command_exists npm; then
        NPM_VERSION=$(npm --version)
        print_success "npm: $NPM_VERSION"
    else
        print_error "npm not found"
        all_ok=false
    fi
    
    # Tesseract (optional)
    if command_exists tesseract; then
        TESSERACT_VERSION=$(tesseract --version 2>&1 | head -1)
        print_success "Tesseract: $TESSERACT_VERSION"
    else
        print_warning "Tesseract not found (optional - other OCR providers available)"
    fi
    
    # pip
    if command_exists pip3; then
        PIP_VERSION=$(pip3 --version 2>&1 | cut -d' ' -f2)
        print_success "pip: $PIP_VERSION"
    else
        print_error "pip3 not found"
        all_ok=false
    fi
    
    if [ "$all_ok" = false ]; then
        echo ""
        print_error "Some prerequisites are missing."
        echo "Would you like to install them automatically? (y/n)"
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            install_system_deps
            check_prerequisites
        else
            echo "Please install the missing dependencies and run this script again."
            exit 1
        fi
    fi
}

# Create virtual environment
setup_python_env() {
    print_step "Setting Up Python Environment"
    
    if [ ! -d "venv" ]; then
        echo "Creating Python virtual environment..."
        python3 -m venv venv
        print_success "Virtual environment created"
    else
        print_success "Virtual environment already exists"
    fi
    
    echo "Activating virtual environment..."
    source venv/bin/activate
    
    echo "Upgrading pip..."
    pip install --upgrade pip
    
    echo "Installing Python dependencies..."
    pip install -r requirements.txt
    
    print_success "Python dependencies installed"
}

# Install Node.js dependencies
setup_node_env() {
    print_step "Setting Up Node.js Environment"
    
    echo "Installing root dependencies..."
    npm install
    print_success "Root dependencies installed"
    
    if [ -d "frontend" ]; then
        echo "Installing frontend dependencies..."
        cd frontend && npm install && cd ..
        print_success "Frontend dependencies installed"
    fi
}

# Create required directories
create_directories() {
    print_step "Creating Required Directories"
    
    directories=("uploads" "training_data" "models" "backups")
    
    for dir in "${directories[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            print_success "Created: $dir/"
        else
            echo "  Already exists: $dir/"
        fi
    done
}

# Setup configuration
setup_config() {
    print_step "Setting Up Configuration"
    
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            cp .env.example .env
            print_success "Created .env from .env.example"
        else
            # Create a minimal .env file
            cat > .env << 'EOF'
# Database
DATABASE_URL=sqlite:///./admission_forms.db

# OCR Configuration
OCR_PROVIDER=tesseract
OCR_ENABLE_TESSERACT=true

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# Environment
ENVIRONMENT=development
EOF
            print_success "Created minimal .env file"
        fi
        print_warning "Edit .env to configure OCR providers and API keys"
    else
        print_success ".env file already exists"
    fi
}

# Initialize database
init_database() {
    print_step "Initializing Database"
    
    # Activate venv if it exists
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    fi
    
    python3 -c "
from backend.database import engine, Base
Base.metadata.create_all(bind=engine)
print('Database tables created successfully')
" 2>/dev/null && print_success "Database initialized" || print_warning "Database will be initialized on first run"
}

# Verify installation
verify_installation() {
    print_step "Verifying Installation"
    
    local all_ok=true
    
    # Check Python packages
    if python3 -c "import fastapi" 2>/dev/null; then
        print_success "FastAPI installed"
    else
        print_error "FastAPI not installed"
        all_ok=false
    fi
    
    if python3 -c "import uvicorn" 2>/dev/null; then
        print_success "Uvicorn installed"
    else
        print_error "Uvicorn not installed"
        all_ok=false
    fi
    
    # Check Node packages
    if [ -d "node_modules" ]; then
        print_success "Root node_modules installed"
    else
        print_error "Root node_modules missing"
        all_ok=false
    fi
    
    if [ -d "frontend/node_modules" ]; then
        print_success "Frontend node_modules installed"
    else
        print_warning "Frontend node_modules missing (run: cd frontend && npm install)"
    fi
    
    # Check directories
    for dir in uploads training_data models; do
        if [ -d "$dir" ]; then
            print_success "Directory exists: $dir/"
        else
            print_error "Directory missing: $dir/"
            all_ok=false
        fi
    done
    
    # Check config
    if [ -f ".env" ]; then
        print_success ".env file exists"
    else
        print_error ".env file missing"
        all_ok=false
    fi
    
    echo ""
    if [ "$all_ok" = true ]; then
        return 0
    else
        return 1
    fi
}

# Print completion message
print_completion() {
    echo -e "\n${GREEN}"
    echo "╔════════════════════════════════════════════════════════════════════╗"
    echo "║                     ✅ Setup Complete!                             ║"
    echo "╚════════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    echo -e "${CYAN}Next Steps:${NC}"
    echo ""
    echo "  1. Activate the virtual environment:"
    echo -e "     ${YELLOW}source venv/bin/activate${NC}"
    echo ""
    echo "  2. Start the application:"
    echo -e "     ${YELLOW}make dev${NC}  or  ${YELLOW}./start.sh start${NC}"
    echo ""
    echo "  3. Access the application:"
    echo -e "     Frontend: ${BLUE}http://localhost:5173${NC}"
    echo -e "     Backend:  ${BLUE}http://localhost:8000${NC}"
    echo -e "     API Docs: ${BLUE}http://localhost:8000/docs${NC}"
    echo ""
    echo -e "${CYAN}Optional Configuration:${NC}"
    echo "  - Edit .env to configure OCR providers (Google Vision, Azure, etc.)"
    echo "  - See QUICK_DEPLOY.md for deployment options"
    echo ""
}

# Main setup function
main() {
    print_header
    
    echo "This script will set up the OCR admission forms system."
    echo "It will install dependencies and configure the environment."
    echo ""
    
    check_prerequisites
    setup_python_env
    setup_node_env
    create_directories
    setup_config
    init_database
    
    if verify_installation; then
        print_completion
    else
        echo ""
        print_error "Setup completed with warnings. Please check the messages above."
        echo "You may need to install missing components manually."
    fi
}

# Run main function
main "$@"
