# Deployment Guide

This guide covers deploying the Student Records Management System to production.

## Table of Contents
1. [Production Checklist](#production-checklist)
2. [Backend Deployment](#backend-deployment)
3. [Frontend Deployment](#frontend-deployment)
4. [Database Setup](#database-setup)
5. [Security Considerations](#security-considerations)
6. [Monitoring](#monitoring)

---

## Production Checklist

Before deploying to production:

- [ ] Configure production database (PostgreSQL recommended)
- [ ] Set up OCR provider API credentials
- [ ] Configure environment variables
- [ ] Enable HTTPS/SSL
- [ ] Set up authentication (if required)
- [ ] Configure file storage and backups
- [ ] Set up monitoring and logging
- [ ] Configure CORS for production URLs
- [ ] Test OCR with sample forms
- [ ] Set up regular database backups
- [ ] Configure firewall rules
- [ ] Set up domain name and DNS
- [ ] Load test the system

---

## Backend Deployment

### Option 1: Docker (Recommended)

1. **Create Dockerfile**

```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY backend ./backend
COPY uploads ./uploads

# Create uploads directory
RUN mkdir -p uploads

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

2. **Build and Run**

```bash
# Build
docker build -t student-records-backend .

# Run
docker run -d \
  -p 8000:8000 \
  -v $(pwd)/uploads:/app/uploads \
  -v $(pwd)/.env:/app/.env \
  --name student-records-backend \
  student-records-backend
```

### Option 2: Traditional Server

1. **Install Dependencies**

```bash
# System packages
sudo apt-get update
sudo apt-get install -y python3.11 python3-pip tesseract-ocr nginx

# Python packages
pip3 install -r requirements.txt
```

2. **Configure Systemd Service**

Create `/etc/systemd/system/student-records.service`:

```ini
[Unit]
Description=Student Records Management System
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/var/www/student-records
Environment="PATH=/usr/local/bin"
ExecStart=/usr/local/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
```

3. **Start Service**

```bash
sudo systemctl daemon-reload
sudo systemctl enable student-records
sudo systemctl start student-records
```

4. **Configure Nginx**

Create `/etc/nginx/sites-available/student-records`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    client_max_body_size 20M;

    # Frontend
    location / {
        root /var/www/student-records/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Uploaded files
    location /uploads {
        proxy_pass http://localhost:8000;
    }
}
```

Enable site:
```bash
sudo ln -s /etc/nginx/sites-available/student-records /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## Frontend Deployment

### Build for Production

```bash
cd frontend
npm install
npm run build
```

This creates optimized files in `frontend/dist/`

### Deploy to Nginx (covered above)

Or deploy to static hosting:

**Netlify:**
```bash
netlify deploy --prod --dir=frontend/dist
```

**Vercel:**
```bash
vercel --prod frontend/dist
```

**AWS S3 + CloudFront:**
```bash
aws s3 sync frontend/dist s3://your-bucket-name
aws cloudfront create-invalidation --distribution-id YOUR_ID --paths "/*"
```

---

## Database Setup

### PostgreSQL (Recommended for Production)

1. **Install PostgreSQL**

```bash
sudo apt-get install postgresql postgresql-contrib
```

2. **Create Database and User**

```sql
sudo -u postgres psql

CREATE DATABASE admission_forms;
CREATE USER student_admin WITH PASSWORD 'secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE admission_forms TO student_admin;
\q
```

3. **Configure Connection**

Update `.env`:
```env
DATABASE_URL=postgresql://student_admin:secure_password_here@localhost:5432/admission_forms
```

4. **Initialize Tables**

```bash
python -c "from backend.database import Base, engine; Base.metadata.create_all(bind=engine)"
```

5. **Set Up Backups**

Create backup script `/usr/local/bin/backup-student-db.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/var/backups/student-records"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# Database backup
pg_dump -U student_admin admission_forms | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Uploads backup
tar -czf $BACKUP_DIR/uploads_$DATE.tar.gz /var/www/student-records/uploads

# Keep only last 30 days
find $BACKUP_DIR -mtime +30 -delete

echo "Backup completed: $DATE"
```

Add to crontab:
```bash
# Daily backup at 2 AM
0 2 * * * /usr/local/bin/backup-student-db.sh
```

---

## Security Considerations

### 1. Environment Variables

Never commit `.env` file to git. Use environment-specific configurations:

```bash
# Development
cp .env.example .env.development

# Production
cp .env.example .env.production
# Edit with production values
```

### 2. API Keys

Store API keys securely:
- Use AWS Secrets Manager, Azure Key Vault, or Google Secret Manager
- Never hardcode in source files
- Rotate keys regularly

### 3. File Upload Security

Update `backend/config.py`:

```python
class Settings(BaseSettings):
    # ... other settings
    
    # File size limit (20MB)
    MAX_FILE_SIZE: int = 20 * 1024 * 1024
    
    # Strict file type validation
    ALLOWED_EXTENSIONS: List[str] = ["jpg", "jpeg", "png", "pdf", "tiff"]
    
    # Secure upload directory
    UPLOAD_DIR: str = "/var/uploads/student-records"
```

### 4. CORS

Update allowed origins:

```python
CORS_ORIGINS: List[str] = [
    "https://your-domain.com",
    "https://www.your-domain.com"
]
```

### 5. Rate Limiting

Add rate limiting (install: `pip install slowapi`):

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/api/upload")
@limiter.limit("10/minute")
async def upload_form(...):
    pass
```

### 6. Authentication (Optional)

For multi-user deployments, add authentication:

```bash
pip install fastapi-users[sqlalchemy]
```

See: https://fastapi-users.github.io/fastapi-users/

---

## Monitoring

### 1. Logging

Configure production logging in `backend/main.py`:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/student-records/app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"{request.method} {request.url}")
    response = await call_next(request)
    logger.info(f"Status: {response.status_code}")
    return response
```

### 2. Health Checks

Already implemented at `/health` endpoint.

Monitor with:
```bash
# Simple check
curl https://your-domain.com/health

# With monitoring service (e.g., UptimeRobot, Pingdom)
```

### 3. OCR Monitoring

Track OCR usage and costs:

```python
# Add to upload endpoint
@app.post("/api/upload")
async def upload_form(...):
    # ... existing code
    
    # Log OCR usage
    logger.info(f"OCR used: {ocr_provider}, pages: {page_count}, cost: ${estimated_cost}")
```

### 4. Database Monitoring

Monitor database:
```sql
-- Check connection count
SELECT count(*) FROM pg_stat_activity;

-- Check database size
SELECT pg_size_pretty(pg_database_size('admission_forms'));

-- Slow queries
SELECT query, mean_exec_time FROM pg_stat_statements 
ORDER BY mean_exec_time DESC LIMIT 10;
```

### 5. Application Monitoring

Use tools like:
- **Sentry** for error tracking
- **Prometheus + Grafana** for metrics
- **ELK Stack** for log aggregation

---

## Performance Optimization

### 1. Database Indexing

Already implemented in models. For large datasets:

```sql
-- Add indexes for frequent searches
CREATE INDEX idx_student_name_trgm ON admission_forms USING gin (student_name gin_trgm_ops);
CREATE INDEX idx_enrollment ON admission_forms(enrollment_number);
```

### 2. Caching

Add Redis for caching:

```bash
pip install redis aioredis
```

```python
from redis import Redis
import pickle

redis_client = Redis(host='localhost', port=6379, db=0)

@app.get("/api/forms/{form_id}")
async def get_form(form_id: int):
    # Try cache first
    cached = redis_client.get(f"form:{form_id}")
    if cached:
        return pickle.loads(cached)
    
    # Get from DB
    form = db.query(AdmissionForm).filter(...).first()
    
    # Cache for 1 hour
    redis_client.setex(f"form:{form_id}", 3600, pickle.dumps(form))
    
    return form
```

### 3. CDN

Use CDN for static files:
- CloudFlare
- AWS CloudFront
- Azure CDN

---

## Scaling

### Horizontal Scaling

1. **Load Balancer**

Use Nginx or HAProxy:

```nginx
upstream backend {
    least_conn;
    server 10.0.1.10:8000;
    server 10.0.1.11:8000;
    server 10.0.1.12:8000;
}

server {
    location /api {
        proxy_pass http://backend;
    }
}
```

2. **Shared File Storage**

Use NFS or S3 for uploads:

```python
# For S3
import boto3

s3_client = boto3.client('s3')

def upload_to_s3(file, bucket, key):
    s3_client.upload_fileobj(file, bucket, key)
    return f"https://{bucket}.s3.amazonaws.com/{key}"
```

---

## Troubleshooting Production Issues

### Backend Not Responding

```bash
# Check service status
sudo systemctl status student-records

# Check logs
sudo journalctl -u student-records -f

# Check port
sudo netstat -tlnp | grep 8000
```

### Database Connection Issues

```bash
# Check PostgreSQL
sudo systemctl status postgresql

# Check connections
sudo -u postgres psql -c "SELECT count(*) FROM pg_stat_activity;"

# Check logs
sudo tail -f /var/log/postgresql/postgresql-14-main.log
```

### High Memory Usage

```bash
# Check memory
free -h
top -o %MEM

# Optimize uvicorn workers
# Reduce workers in systemd service file
ExecStart=/usr/local/bin/uvicorn backend.main:app --workers 2
```

### Slow OCR Processing

- Monitor API quotas and limits
- Consider caching OCR results
- Use batch processing during off-peak hours
- Optimize image preprocessing

---

## Support

For production issues:
1. Check application logs
2. Review system resources (CPU, memory, disk)
3. Verify API credentials and quotas
4. Check network connectivity
5. Review recent changes

---

## Maintenance Schedule

Recommended maintenance tasks:

**Daily:**
- Monitor error logs
- Check API usage and costs

**Weekly:**
- Review backup integrity
- Check disk space
- Monitor database size

**Monthly:**
- Update dependencies
- Rotate API keys
- Review security logs
- Performance optimization

**Quarterly:**
- Full system audit
- Load testing
- Disaster recovery drill

---

For questions or support, contact your system administrator.
