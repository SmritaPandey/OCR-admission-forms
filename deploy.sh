#!/bin/bash
# Production Deployment Script

set -e

echo "=========================================="
echo "OCR Admission Forms - Production Deployment"
echo "=========================================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed"
    echo "   Please install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Error: Docker Compose is not installed"
    echo "   Please install Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

# Check for .env.production
if [ ! -f ".env.production" ]; then
    echo "⚠️  Warning: .env.production not found"
    echo "   Creating from .env.production.example..."
    if [ -f ".env.production.example" ]; then
        cp .env.production.example .env.production
        echo "   ✅ Created .env.production"
        echo "   ⚠️  Please update .env.production with your production values!"
        read -p "   Press Enter to continue after updating .env.production..."
    else
        echo "   ❌ .env.production.example not found"
        exit 1
    fi
fi

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p uploads training_data models backups
chmod -R 755 uploads training_data models backups

# Build and start services
echo ""
echo "🐳 Building Docker images..."
docker-compose -f docker-compose.yml build

echo ""
echo "🚀 Starting services..."
docker-compose -f docker-compose.yml up -d

# Wait for services to be healthy
echo ""
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check service health
echo ""
echo "🏥 Checking service health..."

# Check backend
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "   ✅ Backend is healthy"
else
    echo "   ⚠️  Backend health check failed (may still be starting)"
fi

# Check frontend
if curl -f http://localhost:3000/health > /dev/null 2>&1; then
    echo "   ✅ Frontend is healthy"
else
    echo "   ⚠️  Frontend health check failed (may still be starting)"
fi

# Check database
if docker-compose exec -T postgres pg_isready -U student_admin > /dev/null 2>&1; then
    echo "   ✅ Database is healthy"
else
    echo "   ⚠️  Database health check failed"
fi

echo ""
echo "=========================================="
echo "✅ Deployment Complete!"
echo "=========================================="
echo ""
echo "Services are running:"
echo "  - Frontend: http://localhost:3000"
echo "  - Backend API: http://localhost:8000"
echo "  - API Docs: http://localhost:8000/docs"
echo ""
echo "Useful commands:"
echo "  - View logs: docker-compose logs -f"
echo "  - Stop services: docker-compose down"
echo "  - Restart services: docker-compose restart"
echo "  - View status: docker-compose ps"
echo ""
echo "⚠️  Remember to:"
echo "  1. Update CORS_ORIGINS in .env.production"
echo "  2. Set secure POSTGRES_PASSWORD"
echo "  3. Configure SSL/HTTPS for production"
echo "  4. Set up regular backups"
echo ""
