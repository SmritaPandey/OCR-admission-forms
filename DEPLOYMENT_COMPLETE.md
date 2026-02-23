# 🚀 Complete Deployment Guide

## ✅ Production-Ready Deployment Setup

The project is now fully deployable with Docker, Docker Compose, and production configurations.

---

## 📦 What's Included

### Docker Configuration
- ✅ **Dockerfile.backend** - Production-ready backend container
- ✅ **Dockerfile.frontend** - Optimized frontend container with Nginx
- ✅ **docker-compose.yml** - Complete stack (PostgreSQL + Backend + Frontend)
- ✅ **.dockerignore** - Optimized build context

### Deployment Scripts
- ✅ **deploy.sh** - Quick deployment script
- ✅ **deploy-production.sh** - Full production deployment
- ✅ **scripts/backup.sh** - Automated backup script
- ✅ **scripts/restore.sh** - Restore from backup
- ✅ **scripts/monitor.sh** - System monitoring

### Configuration Files
- ✅ **.env.production.example** - Production environment template
- ✅ **nginx.conf** - Nginx configuration for frontend

### Production Features
- ✅ Health checks for all services
- ✅ Automatic database initialization
- ✅ Volume mounts for persistent data
- ✅ Production-ready CORS configuration
- ✅ Optimized Docker images
- ✅ Backup and restore scripts

---

## 🚀 Quick Deployment

### Option 1: Docker Compose (Recommended)

```bash
# 1. Copy environment file
cp .env.production.example .env.production

# 2. Edit .env.production with your values
nano .env.production

# 3. Deploy
./deploy.sh
```

### Option 2: Manual Docker Compose

```bash
# Build and start
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

---

## 📋 Pre-Deployment Checklist

- [ ] Update `.env.production` with production values
- [ ] Set secure `POSTGRES_PASSWORD`
- [ ] Configure `CORS_ORIGINS` with your domain
- [ ] Set up SSL certificates (for HTTPS)
- [ ] Configure firewall rules
- [ ] Set up domain name and DNS
- [ ] Configure backup schedule
- [ ] Set up monitoring

---

## 🔧 Configuration

### Environment Variables

Key variables in `.env.production`:

```env
# Database
DATABASE_URL=postgresql://student_admin:PASSWORD@postgres:5432/admission_forms
POSTGRES_PASSWORD=YOUR_SECURE_PASSWORD

# OCR Provider
OCR_PROVIDER=craft-trocr

# CORS (update with your domain)
CORS_ORIGINS=https://your-domain.com,https://www.your-domain.com

# Frontend API URL
NEXT_PUBLIC_API_URL=https://api.your-domain.com
```

---

## 🐳 Docker Services

### Services Included

1. **postgres** - PostgreSQL 15 database
   - Port: 5432
   - Data: Persistent volume
   - Health checks enabled

2. **backend** - FastAPI application
   - Port: 8000
   - Workers: 4
   - Health checks enabled
   - Auto-restart on failure

3. **frontend** - React frontend with Nginx
   - Port: 3000 (mapped to 80 in container)
   - Optimized production build
   - Health checks enabled

---

## 📊 Monitoring

### Health Checks

All services include health checks:

```bash
# Check backend
curl http://localhost:8000/health

# Check frontend
curl http://localhost:3000/health

# Check database
docker-compose exec postgres pg_isready -U student_admin
```

### Monitoring Script

```bash
# Run monitoring script
./scripts/monitor.sh
```

This shows:
- Container status
- Health checks
- Resource usage
- Disk usage
- Database size
- Recent errors

---

## 💾 Backup and Restore

### Automated Backups

```bash
# Run backup script
./scripts/backup.sh
```

Backs up:
- Database (PostgreSQL dump)
- Uploads directory
- Training data
- Trained models

### Restore from Backup

```bash
# Run restore script
./scripts/restore.sh
```

### Schedule Backups

Add to crontab:

```bash
# Daily backup at 2 AM
0 2 * * * cd /path/to/project && ./scripts/backup.sh
```

---

## 🔒 Security

### Production Security Checklist

- [ ] Use strong PostgreSQL password
- [ ] Enable HTTPS/SSL
- [ ] Configure firewall (only allow 80, 443, 22)
- [ ] Update CORS_ORIGINS with your domain only
- [ ] Use secrets management for API keys
- [ ] Enable rate limiting
- [ ] Set up authentication (if multi-user)
- [ ] Regular security updates
- [ ] Monitor logs for suspicious activity

### SSL/HTTPS Setup

1. **Get SSL Certificate** (Let's Encrypt):

```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

2. **Update Nginx Configuration**:

See `DEPLOYMENT.md` for full Nginx configuration with SSL.

---

## 📈 Scaling

### Horizontal Scaling

1. **Load Balancer**: Use Nginx or HAProxy
2. **Multiple Backend Instances**: Scale backend service
3. **Shared Storage**: Use S3 or NFS for uploads

### Vertical Scaling

Increase resources in `docker-compose.yml`:

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
```

---

## 🛠️ Maintenance

### Update Application

```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose up -d --build
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f postgres
```

### Restart Services

```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart backend
```

---

## 🐛 Troubleshooting

### Services Not Starting

```bash
# Check logs
docker-compose logs

# Check container status
docker-compose ps

# Check resource usage
docker stats
```

### Database Connection Issues

```bash
# Check database
docker-compose exec postgres psql -U student_admin -d admission_forms

# Check connection string
docker-compose exec backend env | grep DATABASE_URL
```

### Port Conflicts

If ports are already in use:

```yaml
# Update ports in docker-compose.yml
ports:
  - "8001:8000"  # Change 8000 to 8001
```

---

## 📚 Additional Resources

- **DEPLOYMENT.md** - Detailed deployment guide
- **README.md** - Complete project documentation
- **.env.production.example** - Environment configuration template

---

## ✅ Deployment Complete!

Your application is now ready for production deployment!

**Next Steps:**
1. Configure `.env.production`
2. Run `./deploy.sh`
3. Set up SSL/HTTPS
4. Configure monitoring
5. Schedule backups

---

For support, see the main README.md or open an issue.
