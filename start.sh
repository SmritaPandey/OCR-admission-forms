#!/bin/bash
# =============================================================================
# Student Admission Form OCR System - Unified Startup Script
# =============================================================================

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Ports
BACKEND_PORT=8000
FRONTEND_PORT=5173

print_header() {
    echo -e "${BLUE}"
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║       Student Admission Form OCR System                    ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

port_in_use() {
    lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1
}

check_prerequisites() {
    echo -e "${BLUE}Checking prerequisites...${NC}"
    
    if ! command_exists python3; then
        echo -e "${RED}❌ Python 3 not found. Please install Python 3.8+${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Python: $(python3 --version)${NC}"
    
    if ! command_exists node; then
        echo -e "${RED}❌ Node.js not found. Please install Node.js 16+${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Node.js: $(node --version)${NC}"
    
    if ! command_exists npm; then
        echo -e "${RED}❌ npm not found${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ npm: $(npm --version)${NC}"
    
    if command_exists tesseract; then
        echo -e "${GREEN}✓ Tesseract OCR available${NC}"
    else
        echo -e "${YELLOW}⚠ Tesseract not found (optional - other OCR providers available)${NC}"
    fi
}

setup() {
    print_header
    echo -e "${BLUE}Setting up the system...${NC}"
    echo ""
    
    check_prerequisites
    echo ""
    
    # Python dependencies
    echo -e "${BLUE}Installing Python dependencies...${NC}"
    pip3 install -q -r requirements.txt
    echo -e "${GREEN}✓ Python dependencies installed${NC}"
    
    # Frontend dependencies
    echo -e "${BLUE}Installing frontend dependencies...${NC}"
    cd frontend && npm install --silent && cd ..
    echo -e "${GREEN}✓ Frontend dependencies installed${NC}"
    
    # Create directories
    mkdir -p uploads training_data
    echo -e "${GREEN}✓ Created required directories${NC}"
    
    # Create .env if needed
    if [ ! -f .env ] && [ -f .env.example ]; then
        cp .env.example .env
        echo -e "${GREEN}✓ Created .env from .env.example${NC}"
        echo -e "${YELLOW}  → Edit .env to configure OCR providers${NC}"
    fi
    
    # Initialize database
    echo -e "${BLUE}Initializing database...${NC}"
    python3 -c "from backend.database import engine, Base; Base.metadata.create_all(bind=engine)" 2>/dev/null || true
    echo -e "${GREEN}✓ Database initialized${NC}"
    
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  ✅ Setup Complete!                                        ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "Run ${YELLOW}./start.sh start${NC} to launch the application"
}

stop_services() {
    echo -e "${YELLOW}Stopping services...${NC}"
    
    # Kill by PID files
    [ -f .backend.pid ] && kill $(cat .backend.pid) 2>/dev/null && rm -f .backend.pid
    [ -f .frontend.pid ] && kill $(cat .frontend.pid) 2>/dev/null && rm -f .frontend.pid
    
    # Kill any remaining on ports
    lsof -ti:$BACKEND_PORT | xargs kill -9 2>/dev/null || true
    lsof -ti:$FRONTEND_PORT | xargs kill -9 2>/dev/null || true
    
    echo -e "${GREEN}✓ Services stopped${NC}"
}

start_backend() {
    echo -e "${BLUE}Starting backend server...${NC}"
    
    # Check port
    if port_in_use $BACKEND_PORT; then
        echo -e "${YELLOW}Port $BACKEND_PORT in use, stopping existing process...${NC}"
        lsof -ti:$BACKEND_PORT | xargs kill -9 2>/dev/null || true
        sleep 1
    fi
    
    # Start uvicorn
    python3 -m uvicorn backend.main:app --reload --host 0.0.0.0 --port $BACKEND_PORT &
    echo $! > .backend.pid
    
    sleep 3
    
    if curl -s http://localhost:$BACKEND_PORT/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Backend running on http://localhost:$BACKEND_PORT${NC}"
    else
        echo -e "${YELLOW}  Backend starting... (may take a moment)${NC}"
    fi
}

start_frontend() {
    echo -e "${BLUE}Starting frontend server...${NC}"
    
    # Check port
    if port_in_use $FRONTEND_PORT; then
        echo -e "${YELLOW}Port $FRONTEND_PORT in use, stopping existing process...${NC}"
        lsof -ti:$FRONTEND_PORT | xargs kill -9 2>/dev/null || true
        sleep 1
    fi
    
    # Check node_modules
    if [ ! -d "frontend/node_modules" ]; then
        echo -e "${YELLOW}Installing frontend dependencies...${NC}"
        cd frontend && npm install && cd ..
    fi
    
    # Start vite
    cd frontend && npm run dev &
    FRONTEND_PID=$!
    cd ..
    echo $FRONTEND_PID > .frontend.pid
    
    sleep 3
    echo -e "${GREEN}✓ Frontend running on http://localhost:$FRONTEND_PORT${NC}"
}

start_all() {
    print_header
    
    # Check prerequisites quickly
    if ! command_exists python3 || ! command_exists node; then
        echo -e "${RED}Prerequisites missing. Run: ./start.sh setup${NC}"
        exit 1
    fi
    
    # Check Python deps
    if ! python3 -c "import fastapi" 2>/dev/null; then
        echo -e "${YELLOW}Python dependencies missing. Running setup...${NC}"
        setup
    fi
    
    mkdir -p uploads
    
    stop_services 2>/dev/null || true
    echo ""
    
    start_backend
    start_frontend
    
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  ✅ System Running!                                        ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  ${BLUE}Frontend:${NC}  http://localhost:$FRONTEND_PORT"
    echo -e "  ${BLUE}Backend:${NC}   http://localhost:$BACKEND_PORT"
    echo -e "  ${BLUE}API Docs:${NC}  http://localhost:$BACKEND_PORT/docs"
    echo ""
    echo -e "  Stop with: ${YELLOW}./start.sh stop${NC}"
    echo ""
}

show_status() {
    print_header
    echo -e "${BLUE}Service Status:${NC}"
    echo ""
    
    if curl -s http://localhost:$BACKEND_PORT/health > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓ Backend:${NC}  http://localhost:$BACKEND_PORT (running)"
    else
        echo -e "  ${RED}✗ Backend:${NC}  not running"
    fi
    
    if curl -s http://localhost:$FRONTEND_PORT > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓ Frontend:${NC} http://localhost:$FRONTEND_PORT (running)"
    else
        echo -e "  ${RED}✗ Frontend:${NC} not running"
    fi
    echo ""
}

show_help() {
    print_header
    echo "Usage: ./start.sh <command>"
    echo ""
    echo "Commands:"
    echo "  setup     Install all dependencies and configure the system"
    echo "  start     Start backend and frontend servers"
    echo "  stop      Stop all running services"
    echo "  restart   Restart all services"
    echo "  status    Check if services are running"
    echo "  backend   Start only the backend server"
    echo "  frontend  Start only the frontend server"
    echo ""
    echo "Examples:"
    echo "  ./start.sh setup    # First time setup"
    echo "  ./start.sh start    # Start the application"
    echo "  ./start.sh stop     # Stop all services"
    echo ""
}

# Main
case "${1:-help}" in
    setup)
        setup
        ;;
    start)
        start_all
        ;;
    stop)
        stop_services
        ;;
    restart)
        stop_services
        sleep 2
        start_all
        ;;
    status)
        show_status
        ;;
    backend)
        start_backend
        ;;
    frontend)
        start_frontend
        ;;
    help|--help|-h|*)
        show_help
        ;;
esac
