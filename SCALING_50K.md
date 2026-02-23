# Scaling Guide: 50,000+ Students (4-Page Forms + 20–30 Page Attachments)

This guide covers **exact configuration** for running the OCR Admission Forms system at scale:

- **50,000+ students**
- **4-page form** per student
- **~20–30 page PDF** attachments per student (admit cards, certificates, etc.)

**Per-student footprint:** 1 PDF ≈ 24–34 pages (4 form + 20–30 docs) → ~5–15 MB per PDF typical.

---

## 1. Scale Snapshot

| Metric | Estimate |
|--------|----------|
| Students | 50,000+ |
| Form pages | 200,000 (50k × 4) |
| Attachment pages | ~1–1.5 million (50k × 20–30) |
| Total PDF pages | ~1.2–1.7 million |
| Raw PDF storage | **~500 GB – 1 TB** |
| Database (PostgreSQL + indexes) | **~20–50 GB** |
| OCR cache / temp (if enabled) | **~50–100 GB** |
| **Total storage (excluding backups)** | **~600 GB – 1.2 TB** |

---

## 2. Database

### Mandatory: PostgreSQL

**SQLite is not suitable** for 50k+ students with concurrent batch uploads, search, and exports. Use **PostgreSQL**.

| Setting | Value |
|--------|--------|
| **Database** | PostgreSQL 14+ |
| **Connection** | `postgresql://USER:PASS@HOST:5432/admission_forms` |

**Example `.env`:**
```env
DATABASE_URL=postgresql://student_admin:YOUR_SECURE_PASSWORD@localhost:5432/admission_forms
```

**Recommended DB sizing:**
- **RAM:** 8–16 GB for Postgres (shared_buffers ~2–4 GB).
- **Disk:** SSD, 100+ GB for DB + indexes + growth.
- **Connections:** `max_connections` ≥ `(uvicorn_workers × 2) + 20` (e.g. 8 workers → 40+).

**Indexes:** The app creates indexes on `student_name`, `aadhar_number`, `roll_number`, `college_roll_no`, `du_portal_form_number`, etc. Ensure `CREATE INDEX` runs (via migrations or `Base.metadata.create_all`).

---

## 3. File Upload Limits

### Max file size (critical)

Each student upload is **one PDF** (4 form + 20–30 doc pages). Many will **exceed 10 MB**.

| Setting | Default | **50k-scale recommendation** |
|--------|---------|------------------------------|
| **MAX_FILE_SIZE** | 10 MB | **100 MB** (up to 150 MB if you have 30+ page docs) |

**`.env`:**
```env
MAX_FILE_SIZE=104857600
```
(104857600 = 100 MB)

**Other layers:**
- **Nginx** (if used): `client_max_body_size 100m;`
- **Load balancer / reverse proxy:** equivalent limit ≥ 100 MB.

---

## 4. Batch Processing & Concurrency

| Setting | Default | **50k-scale recommendation** |
|--------|---------|------------------------------|
| **BATCH_MAX_CONCURRENT** | 5 | **10–20** (tune with OCR provider limits and CPU) |
| **BATCH_QUEUE_BACKEND** | `memory` | **`redis`** when supported (for multi-worker, durable jobs) |

**`.env`:**
```env
BATCH_MAX_CONCURRENT=12
BATCH_QUEUE_BACKEND=redis
```

**Note:** The app currently uses an in-memory job store. For 50k batches across multiple workers, a **Redis-backed queue** is recommended; that may require implementation work. Until then, use a **single backend process** (or carefully coordinated workers) and **BATCH_MAX_CONCURRENT=10–15**.

---

## 5. Backend Server (Uvicorn)

| Setting | Default | **50k-scale recommendation** |
|--------|---------|------------------------------|
| **Host** | `0.0.0.0` (online) / `127.0.0.1` (desktop) | `0.0.0.0` for server |
| **Port** | 8000 | 8000 (or your choice) |
| **Workers** | 1 (dev) / 4 (Docker) | **8–16** for API + batch |

**Example:**
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 8
```

**Systemd example** (adjust paths and user):
```ini
[Service]
ExecStart=/path/to/venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 8
```

**Resources:**
- **CPU:** 8+ cores recommended for OCR + parallel batch.
- **RAM:** 16–32 GB (backend + OCR libs + Postgres on same machine) or scale out DB.

---

## 6. Form Layout: 4-Page Forms + Attachments

The pipeline assumes:
- **Pages 1–4:** admission form (`FORM_PAGE_COUNT = 4` in code).
- **Pages 5+:** supporting documents (auto-extracted).

**Batch upload:** use **`pages_per_form=4`** when calling the batch API (e.g. from the UI or direct API).

---

## 7. OCR Provider & Throughput

Rough page throughput (single key, typical tiers):

| Provider | Typical rate | 1.2M pages (50k × 24) |
|----------|--------------|------------------------|
| Google Cloud Vision | ~1,000–1,800/min | ~11–20 hours |
| Google Document AI | ~500–1,000/min | ~20–40 hours |
| Azure Document Intelligence | ~15–60/min (default) | days |
| Tesseract / CRAFT+TR-OCR (local) | CPU/GPU bound | varies |

**Recommendations:**
- **Cloud:** Use **Google Vision** or **Document AI**; consider **higher quotas** and **multiple service accounts** for parallel batches.
- **Rate limiting:** Respect provider limits (e.g. Vision 1800/min). `BATCH_MAX_CONCURRENT` and worker count indirectly cap concurrent OCR calls.
- **Caching:** Keep `OCR_CACHE_ENABLED=true` to avoid re-OCR of same pages.

**`.env` (example – Google Vision):**
```env
OCR_PROVIDER=google-vision
OCR_ENABLE_GOOGLE_VISION=true
GOOGLE_APPLICATION_CREDENTIALS=/path/to/google-cloud-credentials.json
GOOGLE_CLOUD_PROJECT_ID=your-project-id
```

---

## 8. Storage (Uploads & Optional Object Storage)

| Path | Purpose | **50k-scale size** |
|------|---------|--------------------|
| **UPLOAD_DIR** | Form PDFs + extracted document files | **~500 GB – 1 TB** |

**`.env`:**
```env
UPLOAD_DIR=/data/ocr-admission/uploads
```

**Best practices:**
- Use a **dedicated volume** or **mount** for `UPLOAD_DIR` (not the OS disk).
- **Backups:** Snapshot or backup `UPLOAD_DIR` and the DB regularly.
- **Object storage (S3/GCS):** Not wired in by default. For 50k scale, consider moving blob storage to S3/GCS and updating the app to read/write there.

---

## 9. Frontend / API Base URL

- **Online:** Point frontend to backend via `VITE_API_BASE_URL` (or `NEXT_PUBLIC_API_URL` for Next.js) and your domain, e.g. `https://api.yourdomain.com`.
- **CORS:** Set `CORS_ORIGINS` to your frontend origins (comma-separated).

```env
CORS_ORIGINS=https://app.yourdomain.com,https://yourdomain.com
```

---

## 10. Example `.env` for 50k-Scale (Online)

```env
# Database
DATABASE_URL=postgresql://student_admin:SECURE_PASSWORD@dbhost:5432/admission_forms

# File upload
MAX_FILE_SIZE=104857600
UPLOAD_DIR=/data/ocr-admission/uploads

# Batch
BATCH_MAX_CONCURRENT=12
BATCH_QUEUE_BACKEND=memory

# Form layout
# Use pages_per_form=4 in batch API

# OCR (Google Vision example)
OCR_PROVIDER=google-vision
OCR_ENABLE_GOOGLE_VISION=true
OCR_ENABLE_TESSERACT=true
GOOGLE_APPLICATION_CREDENTIALS=/path/to/google-cloud-credentials.json
GOOGLE_CLOUD_PROJECT_ID=your-project-id

# App
ENVIRONMENT=production
CORS_ORIGINS=https://app.yourdomain.com
```

---

## 11. Desktop vs Online

| Aspect | **Desktop** | **Online (50k scale)** |
|--------|-------------|-------------------------|
| **Database** | SQLite (local) | **PostgreSQL** |
| **Server** | Embedded backend, `127.0.0.1:8000` | Uvicorn `0.0.0.0:8000`, 8–16 workers |
| **Upload dir** | AppData / local `data` | Central `UPLOAD_DIR` (large volume) |
| **MAX_FILE_SIZE** | 10 MB default | **100 MB+** |
| **BATCH_MAX_CONCURRENT** | 5 | **10–20** |
| **OCR** | Local / optional cloud | **Cloud (Vision/Doc AI)** recommended |
| **Storage** | Single machine | **~600 GB – 1.2 TB** provisioned |

The **desktop** app is for smaller, local use. **50k+ students with 4+20–30 page PDFs** should run **online** with the configuration above.

---

## 12. Checklist for 50k Scale

- [ ] **PostgreSQL** configured; `DATABASE_URL` set.
- [ ] **MAX_FILE_SIZE=104857600** (100 MB); proxy/nginx `client_max_body_size` ≥ 100 MB.
- [ ] **UPLOAD_DIR** on a large, dedicated volume (~500 GB – 1 TB).
- [ ] **BATCH_MAX_CONCURRENT=10–20**; **pages_per_form=4** in batch uploads.
- [ ] **8+ Uvicorn workers**; 8+ CPU cores, 16–32 GB RAM.
- [ ] **OCR** provider (e.g. Google Vision) configured; quotas sufficient for ~1.2M+ pages.
- [ ] **CORS_ORIGINS** set for production frontend.
- [ ] **Backups** for DB and `UPLOAD_DIR` scheduled and tested.

---

## 13. Multi-user & role-based access (RBAC)

The app supports **multiple users** and **role-based access**:

- **Roles:** `admin`, `staff`, `viewer`.  
- **Admin:** Full access (users, training, bulk delete, all writes).  
- **Staff:** Upload, verify/edit, search, export, documents. No training or user management.  
- **Viewer:** Read-only (forms, students, search).

**Config:** `AUTH_DISABLED=0` for online; set `JWT_SECRET`, optionally `SEED_ADMIN_PASSWORD` for first admin.  
See **Procurement & software** doc for auth setup.

---

## 14. References

- **Config:** `backend/config.py`
- **Batch processor:** `backend/utils/batch_processor.py`
- **Document extractor:** `backend/utils/document_extractor.py` (`FORM_PAGE_COUNT = 4`)
- **Deployment:** `DEPLOYMENT.md`, `docker-compose.yml`
- **Procurement & software:** [PROCUREMENT_AND_SOFTWARE_REQUIREMENTS.md](PROCUREMENT_AND_SOFTWARE_REQUIREMENTS.md) — domain, hosting, SSL, database, OCR costs, auth/RBAC, and full software stack.
