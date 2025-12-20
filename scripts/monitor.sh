#!/bin/bash
# System Monitoring Script

echo "=========================================="
echo "System Monitoring - $(date)"
echo "=========================================="
echo ""

# Docker containers status
echo "🐳 Docker Containers:"
docker-compose ps
echo ""

# Service health checks
echo "🏥 Health Checks:"
echo -n "  Backend: "
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Healthy"
else
    echo "❌ Unhealthy"
fi

echo -n "  Frontend: "
if curl -f http://localhost:3000/health > /dev/null 2>&1; then
    echo "✅ Healthy"
else
    echo "❌ Unhealthy"
fi

echo -n "  Database: "
if docker-compose exec -T postgres pg_isready -U student_admin > /dev/null 2>&1; then
    echo "✅ Healthy"
else
    echo "❌ Unhealthy"
fi
echo ""

# Resource usage
echo "💻 Resource Usage:"
echo "  CPU:"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" | grep -E "CONTAINER|ocr-admission"
echo ""

# Disk usage
echo "💾 Disk Usage:"
df -h | grep -E "Filesystem|/dev/"
echo ""

# Database size
echo "🗄️  Database Size:"
docker-compose exec -T postgres psql -U student_admin -d admission_forms -c "SELECT pg_size_pretty(pg_database_size('admission_forms'));" 2>/dev/null || echo "  Unable to connect to database"
echo ""

# Recent logs
echo "📋 Recent Errors (last 20 lines):"
docker-compose logs --tail=20 | grep -i error || echo "  No recent errors"
echo ""
