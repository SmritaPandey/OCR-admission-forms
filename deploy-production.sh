#!/bin/bash
# Production Deployment with Nginx and SSL

set -e

echo "=========================================="
echo "OCR Admission Forms - Full Production Deployment"
echo "=========================================="
echo ""

# Check prerequisites
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed"
    exit 1
fi

if ! command -v nginx &> /dev/null; then
    echo "⚠️  Warning: Nginx is not installed"
    echo "   Nginx is recommended for production with SSL"
fi

# Load environment variables
if [ -f ".env.production" ]; then
    export $(cat .env.production | grep -v '^#' | xargs)
else
    echo "❌ Error: .env.production not found"
    exit 1
fi

# Build images
echo "🐳 Building Docker images..."
docker-compose -f docker-compose.yml build --no-cache

# Stop existing containers
echo "🛑 Stopping existing containers..."
docker-compose -f docker-compose.yml down

# Start services
echo "🚀 Starting services..."
docker-compose -f docker-compose.yml up -d

# Wait for services
echo "⏳ Waiting for services to start..."
sleep 15

# Initialize database
echo "🗄️  Initializing database..."
docker-compose exec -T backend python -c "
from backend.database import Base, engine
Base.metadata.create_all(bind=engine)
print('Database initialized')
" || echo "⚠️  Database initialization skipped (may already exist)"

# Health checks
echo ""
echo "🏥 Running health checks..."
BACKEND_HEALTHY=false
FRONTEND_HEALTHY=false

for i in {1..30}; do
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        BACKEND_HEALTHY=true
        break
    fi
    sleep 2
done

for i in {1..30}; do
    if curl -f http://localhost:3000/health > /dev/null 2>&1; then
        FRONTEND_HEALTHY=true
        break
    fi
    sleep 2
done

if [ "$BACKEND_HEALTHY" = true ]; then
    echo "   ✅ Backend is healthy"
else
    echo "   ❌ Backend health check failed"
    echo "   Check logs: docker-compose logs backend"
fi

if [ "$FRONTEND_HEALTHY" = true ]; then
    echo "   ✅ Frontend is healthy"
else
    echo "   ❌ Frontend health check failed"
    echo "   Check logs: docker-compose logs frontend"
fi

# Display status
echo ""
echo "=========================================="
echo "✅ Deployment Status"
echo "=========================================="
docker-compose ps

echo ""
echo "📊 Service URLs:"
echo "  - Frontend: http://localhost:3000"
echo "  - Backend: http://localhost:8000"
echo "  - API Docs: http://localhost:8000/docs"
echo ""
echo "📝 Next Steps:"
echo "  1. Configure Nginx reverse proxy (see DEPLOYMENT.md)"
echo "  2. Set up SSL certificates (Let's Encrypt)"
echo "  3. Configure firewall rules"
echo "  4. Set up monitoring and backups"
echo "  5. Update CORS_ORIGINS with your domain"
echo ""
