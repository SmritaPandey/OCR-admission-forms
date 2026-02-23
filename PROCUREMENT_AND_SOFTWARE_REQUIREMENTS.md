# Procurement & Software Requirements  
## 50k-Scale OCR Admission Forms (Online Deployment)

This document lists **what you need to buy or provision**, **rough costs**, **which companies offer it**, and **all software requirements** for hosting the OCR Admission Forms system at 50,000+ students (4-page forms + 20–30 page attachments).

**Prices are indicative (INR/USD) and can change.** Always confirm with the vendor before purchase.

---

## 1. Domain Name

### What is required
- One **domain** for the application (e.g. `admission-forms.yourcollege.ac.in` or `ocrforms.yourcollege.edu.in`).
- **Registrar:** Whoever you buy the domain from (e.g. GoDaddy, Namecheap, DomainIndia, Nettigritty, or your institution’s registrar).

### How much & costing

| TLD | Typical cost (per year) | Company examples |
|-----|-------------------------|-------------------|
| **.in** | ₹600–800 (~$8–10) | DomainIndia, Nettigritty, GoDaddy India, MilesWeb |
| **.co.in** | ₹500–700 (~$6–9) | Same as above |
| **.com** | ₹1,150–1,500 (~$14–18) | GoDaddy, Namecheap, Google Domains, Cloudflare |
| **.ac.in** (academic) | Varies | Often through ERNET / NIC or your college’s IT |

*GST (18%) usually extra. Renewal often similar to first-year.*

### Recommendation
- Use **.ac.in** if your college already has one (e.g. subdomain like `admission.yourcollege.ac.in`) — often **no extra domain cost**.
- Otherwise **.in** or **.co.in** for India; **.com** if you need a global presence.

### Companies (examples)
- **India:** DomainIndia, Nettigritty, MilesWeb, GoDaddy India, BigRock  
- **Global:** GoDaddy, Namecheap, Google Domains, Cloudflare Registrar

---

## 2. Hosting Space (Compute + Storage)

### What is required
- **Application server:** Runs backend (Python/FastAPI) + frontend (Node/React). Needs **8+ vCPU**, **16–32 GB RAM**, **Ubuntu 22.04 LTS** (or similar).
- **Storage for uploads:** **500 GB – 1 TB** for form PDFs and extracted documents (see [SCALING_50K.md](SCALING_50K.md)).

You can either:
- **A)** One VM with app + Postgres + uploads (simpler, lower cost), or  
- **B)** Separate **app server** + **database server** (e.g. AWS RDS) + **storage** (e.g. EBS).

### How much & costing (ballpark monthly)

| Option | Spec | Storage | Approx monthly cost | Company |
|--------|------|---------|---------------------|---------|
| **VPS (all-in-one)** | 8 GB RAM, 4 vCPU | 500 GB–1 TB add-on | $80–150 (₹6,500–12,500) | DigitalOcean, Linode, Vultr, AWS Lightsail |
| **Cloud VM (app only)** | 8 vCPU, 32 GB RAM | — | $150–250 (₹12,500–21,000) | AWS EC2, GCP CE, Azure VM |
| **+ Block storage** | — | 500 GB SSD | $40–50 (₹3,300–4,200) | AWS EBS gp3, DO Volumes, Linode Block Storage |
| **+ Block storage** | — | 1 TB SSD | $80–100 (₹6,600–8,300) | Same |

*Reserved / 1-year commits usually 30–40% cheaper.*

### Recommendation
- **College has data center / servers:** Use **college infrastructure** for VM + storage (cost as per college policy).
- **Cloud:** **DigitalOcean / Linode / Vultr** for simplicity; **AWS / GCP / Azure** if you need managed DB, compliance, or already use them.

### Companies (examples)
- **VPS:** DigitalOcean, Linode (Akamai), Vultr, AWS Lightsail, Hetzner  
- **Cloud:** AWS, Google Cloud, Microsoft Azure  
- **College:** Institutional DC, ERNET, NIC, or local hosting as per college choice

---

## 3. SSL (HTTPS)

### What is required
- **TLS certificate** so the site is served over **HTTPS**.
- **Free options** are enough for most deployments.

### How much & costing

| Option | Cost | Company / Tool |
|--------|------|----------------|
| **Let’s Encrypt** | **Free** | Automated (Certbot) on your server |
| **Cloudflare Universal SSL** | **Free** | Cloudflare (Free plan) |
| **Paid SSL** | ₹2,000–15,000/year | Sectigo, DigiCert, Comodo (usually overkill) |

### Recommendation
- Use **Let’s Encrypt** (Certbot) **or** **Cloudflare Free** (proxy + SSL). **No need to pay for SSL** for this use case.

### Companies / tools
- **Let’s Encrypt:** [letsencrypt.org](https://letsencrypt.org) — used via **Certbot** on nginx/Apache  
- **Cloudflare:** [cloudflare.com](https://cloudflare.com) — Free plan includes SSL  
- **Paid:** Sectigo, DigiCert, etc. (only if org policy requires it)

---

## 4. Database Server (8 GB RAM)

### What is required
- **PostgreSQL 14+** with **8 GB RAM** (recommended for 50k students).  
- **100+ GB SSD** for database + indexes + growth.

You can use:
- **Managed DB** (AWS RDS, GCP Cloud SQL, Azure Database for PostgreSQL), or  
- **Self‑hosted** Postgres on your own VM (same as app server or separate).

### How much & costing (ballpark monthly)

| Option | Spec | Approx monthly cost | Company |
|--------|------|---------------------|---------|
| **AWS RDS PostgreSQL** | db.t3.large (2 vCPU, 8 GB RAM) + 100 GB | ~$120–170 (₹10,000–14,000) | AWS |
| **GCP Cloud SQL** | 2 vCPU, 8 GB RAM + 100 GB | ~$100–150 (₹8,300–12,500) | Google Cloud |
| **Azure Database for PostgreSQL** | 2 vCPU, 8 GB RAM | ~$100–150 (₹8,300–12,500) | Microsoft Azure |
| **Self‑hosted on same VPS** | Use part of 16–32 GB VM | $0 extra (included in VM) | Your VM provider |
| **DigitalOcean Managed DB** | 2 vCPU, 8 GB RAM | ~$60–90 (₹5,000–7,500) | DigitalOcean |

*Reserved / committed use discounts apply.*

### Recommendation
- **“As per college choice”:** Use **college‑provided PostgreSQL** (8 GB RAM, 100+ GB) if available — **cost per college policy**.
- **Cloud:** **AWS RDS** or **GCP Cloud SQL** if you already use AWS/GCP; **DigitalOcean Managed DB** for simpler setup.

### Companies (examples)
- **Managed:** AWS RDS, Google Cloud SQL, Azure Database for PostgreSQL, DigitalOcean Managed Databases  
- **Self‑hosted:** On your VPS (DigitalOcean, Linode, AWS EC2, etc.) or **college server**

---

## 5. Anything Else?

### 5.1 OCR API (Google Cloud Vision)

- **What:** Cloud OCR for form + document pages.  
- **Usage:** ~1.2–1.7 million pages (50k students × 24–34 pages).  
- **Cost (Google Vision):**  
  - First 1,000 units/month **free**.  
  - Next ~5M: **$1.50 per 1,000 units** → **~$1,800–2,500** one‑time for full batch.  
  - Higher tiers: **$0.60 per 1,000** (volume discount).  
- **Company:** **Google Cloud** (Vision API).  
- **Alternatives:** Google Document AI, Azure Document Intelligence, AWS Textract (pricing differs).

### 5.2 Backup Storage

- **What:** Backups of **database** + **upload files** (500 GB–1 TB).  
- **Size:** ~600 GB–1.2 TB (compressed less).  
- **Cost:** ~$20–60/month (₹1,600–5,000) for object storage (S3, GCS, etc.) or backup service.  
- **Company:** AWS S3, Google Cloud Storage, Azure Blob, Backblaze B2, or college backup system.

### 5.3 Optional: Redis

- **What:** For batch job queue at 50k scale (when implemented).  
- **Cost:** Small managed Redis **~$15–40/month** or **free** if self‑hosted on app VM.  
- **Company:** AWS ElastiCache, Redis Cloud, or self‑hosted.

### 5.4 Auth & multi-user (RBAC)

- **What:** **Multi-user, role-based access** is built in. Roles: **admin**, **staff**, **viewer**.
  - **Admin:** Full access (users CRUD, training, bulk delete, all write operations).
  - **Staff:** Upload, verify/edit forms and students, search, export, documents. No training, no user management.
  - **Viewer:** Read-only (forms, students, search). No upload, edit, or export.
- **Auth:** JWT-based login (`/api/auth/login`). Config: `JWT_SECRET`, `JWT_EXPIRE_MINUTES`, `AUTH_DISABLED`.
- **Seed admin:** Set `SEED_ADMIN_PASSWORD` (and optionally `SEED_ADMIN_USERNAME`, default `admin`) before first run; an admin user is created if the `users` table is empty.
- **Desktop:** Auth is **disabled by default** (`AUTH_DISABLED=1`) when running as the packaged desktop app.
- **Cost:** No extra infra. Use a strong `JWT_SECRET` in production.

### 5.5 Optional: CDN

- **What:** Faster static assets (frontend JS/CSS).  
- **Cost:** **Cloudflare Free** often enough.  
- **Company:** Cloudflare, Fastly, AWS CloudFront, etc.

### 5.6 Email (optional)

- **What:** Notifications, password reset, etc. if you add auth.  
- **Cost:** Varies (SendGrid, AWS SES, etc.); can be **free** tiers.

---

## 6. Summary Table: What, How Much, Which Company

| Item | Required? | Rough cost | Company / option |
|------|-----------|------------|-------------------|
| **Domain** | Yes | ₹500–1,500/year (~$6–18) | DomainIndia, GoDaddy, Namecheap, ERNET, college |
| **Hosting (VM)** | Yes | $80–250/month (₹6,500–21,000) | DO, Linode, Vultr, AWS, GCP, Azure, **college** |
| **Storage (500 GB–1 TB)** | Yes | $40–100/month (₹3,300–8,300) | Same as VM / EBS / DO Volumes |
| **SSL** | Yes | **Free** | Let’s Encrypt, Cloudflare |
| **Database 8 GB** | Yes | $0–170/month | AWS RDS, GCP Cloud SQL, Azure, DO Managed DB, **college** |
| **OCR API (Google Vision)** | Yes (if cloud OCR) | ~$1,800–2,500 one‑time* | Google Cloud |
| **Backups** | Recommended | $20–60/month | S3, GCS, Azure Blob, college backup |
| **Redis** | Optional | $0–40/month | ElastiCache, Redis Cloud, self‑hosted |
| **CDN** | Optional | **Free** (Cloudflare) | Cloudflare |

*One‑time for initial 50k batch; ongoing usage depends on new uploads.*

---

## 7. Example Monthly Cost Ranges

### 7.1 Cloud (AWS / GCP style)

- App VM (8 vCPU, 32 GB): ~$150–200  
- Storage 1 TB: ~$80–100  
- RDS 8 GB PostgreSQL: ~$120–160  
- Backups: ~$30–50  
- **Total:** **~$380–510/month** (₹31,500–42,000) before OCR.

### 7.2 Simpler cloud (e.g. DigitalOcean)

- Droplet 8 GB + 4 vCPU: ~$48–84  
- Volume 1 TB: ~$100  
- Managed Postgres 8 GB: ~$60–90  
- **Total:** **~$210–275/month** (₹17,500–23,000) before OCR.

### 7.3 College‑owned infrastructure

- Domain: as above (or ₹0 if subdomain).  
- VM + storage + DB: **as per college policy** (often no direct cloud bill).  
- OCR: **Google Cloud** ~$1,800–2,500 one‑time for full batch.  
- SSL: **Free** (Let’s Encrypt / Cloudflare).

---

## 8. Software Requirements

### 8.0 Auth (multi-user, RBAC)

- **python-jose** (JWT), **passlib[bcrypt]** (password hashing).  
- **Backend:** `/api/auth/config`, `/api/auth/login`, `/api/auth/me`; `/api/users/` CRUD (admin only).  
- **Frontend:** Login page, role-based sidebar (Upload/Batch for staff+; Training/Users for admin), Users management page.

### 8.1 Server OS

| Software | Version | Purpose |
|----------|---------|--------|
| **Ubuntu Server** | 22.04 LTS (recommended) | OS |
| **AlmaLinux / RHEL** | 8 / 9 | Alternative Linux |

### 8.2 Runtime & language

| Software | Version | Purpose |
|----------|---------|--------|
| **Python** | 3.10 / 3.11 | Backend |
| **Node.js** | 18 LTS or 20 LTS | Frontend build (and runtime if SSR) |
| **npm** or **pnpm** | Latest stable | Frontend deps |

### 8.3 Database

| Software | Version | Purpose |
|----------|---------|--------|
| **PostgreSQL** | 14+ | Primary database |

### 8.4 Web & reverse proxy

| Software | Version | Purpose |
|----------|---------|--------|
| **Nginx** | Latest stable | Reverse proxy, static files, `client_max_body_size 100m` |

### 8.5 Application servers

| Software | Purpose |
|----------|--------|
| **Uvicorn** | ASGI server for FastAPI backend |
| **Systemd** | Run Uvicorn (and optionally frontend) as services |

### 8.6 Backend (Python) – from `requirements.txt`

- **fastapi**, **uvicorn**, **sqlalchemy**, **pydantic**, **pydantic-settings**  
- **pillow**, **pytesseract**, **PyMuPDF**, **pdf2image**, **numpy**  
- **python-multipart**, **requests**  
- **pandas**, **openpyxl**, **reportlab** (export)  
- **psycopg2-binary** (PostgreSQL)  
- **google-cloud-vision**, **google-cloud-documentai** (if using Google OCR)  
- **transformers**, **torch**, **torchvision** (if using local CRAFT+TR-OCR)

### 8.7 Frontend (Node)

- **React**, **Vite**, **TypeScript**  
- **axios** (API client)  
- Plus rest of `frontend/package.json` deps.

### 8.8 Optional

| Software | Purpose |
|----------|--------|
| **Tesseract OCR** | Local OCR (optional if using only cloud) |
| **Redis** | Batch queue at scale (when implemented) |
| **Certbot** | Let’s Encrypt SSL automation |
| **Docker** | Optional containerized deploy |

### 8.9 SSL

- **Let’s Encrypt** certs via **Certbot**, **or**  
- **Cloudflare** (Free) for proxy + SSL.

---

## 9. Quick Checklist

**Procurement**

- [ ] Domain (or college subdomain)  
- [ ] VM (8+ vCPU, 16–32 GB RAM) or college server  
- [ ] 500 GB–1 TB storage for uploads  
- [ ] PostgreSQL 8 GB (managed or self‑hosted)  
- [ ] SSL (Let’s Encrypt or Cloudflare — free)  
- [ ] Google Cloud project + Vision API (if cloud OCR)  
- [ ] Backup storage (S3/GCS/college)

**Software**

- [ ] Ubuntu 22.04 LTS (or approved Linux)  
- [ ] Python 3.10/3.11, Node 18/20, PostgreSQL 14+  
- [ ] Nginx, Uvicorn, systemd  
- [ ] Backend deps (`requirements.txt`), frontend deps (`frontend/package.json`)  
- [ ] Certbot or Cloudflare for SSL  

**Auth (multi-user, RBAC)**

- [ ] `JWT_SECRET` set to a long random value in production  
- [ ] `AUTH_DISABLED=0` for online deployment; `1` for desktop single-user  
- [ ] `SEED_ADMIN_PASSWORD` set on first deploy to create initial admin (optional)  

**Config**

- [ ] `MAX_FILE_SIZE=104857600`, `UPLOAD_DIR`, `DATABASE_URL`  
- [ ] `BATCH_MAX_CONCURRENT`, `pages_per_form=4`  
- [ ] CORS, `ENVIRONMENT=production`  
- [ ] Nginx `client_max_body_size 100m`  

See **[SCALING_50K.md](SCALING_50K.md)** for detailed configuration.

---

*Prices and product names are indicative. Verify with respective providers and your institution’s policies before procurement.*
