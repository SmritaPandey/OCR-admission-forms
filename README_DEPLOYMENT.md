# 🚀 Quick Deployment Guide

## One-Command Deployment

```bash
./deploy.sh
```

That's it! The script will:
1. ✅ Check prerequisites (Docker, Docker Compose)
2. ✅ Create necessary directories
3. ✅ Build Docker images
4. ✅ Start all services
5. ✅ Run health checks

---

## What Gets Deployed

- **PostgreSQL Database** - Production-ready database
- **Backend API** - FastAPI with 4 workers
- **Frontend** - React app with Nginx
- **Health Checks** - Automatic monitoring
- **Persistent Storage** - Data survives restarts

---

## Configuration

1. **Copy environment file**:
   ```bash
   cp .env.production.example .env.production
   ```

2. **Edit `.env.production`**:
   - Set `POSTGRES_PASSWORD` (secure password)
   - Update `CORS_ORIGINS` with your domain
   - Configure OCR providers

3. **Deploy**:
   ```bash
   ./deploy.sh
   ```

---

## Access Your Application

After deployment:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

---

## Useful Commands

```bash
# View logs
make logs

# Check health
make health

# Run backup
make backup

# Monitor system
make monitor

# Stop services
make down

# Restart services
make restart
```

---

## Production Checklist

Before going live:
- [ ] Update `.env.production` with production values
- [ ] Set secure passwords
- [ ] Configure SSL/HTTPS
- [ ] Set up domain and DNS
- [ ] Configure firewall
- [ ] Set up backups
- [ ] Enable monitoring

---

## Full Documentation

- **[DEPLOYMENT_COMPLETE.md](DEPLOYMENT_COMPLETE.md)** - Complete deployment guide
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Detailed production setup
- **[README.md](README.md)** - Project documentation

---

**Ready to deploy!** 🚀
