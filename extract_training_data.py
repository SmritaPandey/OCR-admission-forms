"""Extract all verified training data from admission_forms.db for VLM training."""
import sqlite3
import json
import os
from pathlib import Path

PROJECT = Path(__file__).parent

# Check all DB locations
dbs = ["admission_forms.db", "data/admission_forms.db"]
all_forms = []

for db_path in dbs:
    full = PROJECT / db_path
    if not full.exists():
        continue
    
    conn = sqlite3.connect(str(full))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Get column names
    c.execute("PRAGMA table_info(admission_forms)")
    columns = [r[1] for r in c.fetchall()]
    
    # Get all verified forms (or any with populated fields)
    c.execute("SELECT * FROM admission_forms")
    rows = c.fetchall()
    
    print(f"\n{'='*70}")
    print(f"  Database: {db_path}")
    print(f"  Total forms: {len(rows)}")
    print(f"  Columns: {len(columns)}")
    
    # Count by status
    status_counts = {}
    for row in rows:
        s = row["status"] if "status" in row.keys() else "unknown"
        status_counts[s] = status_counts.get(s, 0) + 1
    print(f"  Status breakdown: {status_counts}")
    
    # For each form, count non-empty fields
    for row in rows:
        fields = {}
        skip_cols = {"id", "filename", "file_path", "upload_date", "ocr_provider", 
                     "status", "student_profile_id", "extracted_data"}
        
        for col in columns:
            if col in skip_cols:
                continue
            val = row[col] if col in row.keys() else None
            if val and str(val).strip():
                fields[col] = str(val).strip()
        
        file_path = row["file_path"] if "file_path" in row.keys() else None
        filename = row["filename"] if "filename" in row.keys() else None
        status = row["status"] if "status" in row.keys() else None
        form_id = row["id"] if "id" in row.keys() else None
        
        all_forms.append({
            "form_id": form_id,
            "filename": filename,
            "file_path": file_path,
            "status": status,
            "field_count": len(fields),
            "fields": fields,
            "db": db_path,
        })
    
    conn.close()

# Show stats
print(f"\n{'='*70}")
print(f"  TOTAL FORMS FOUND: {len(all_forms)}")
print(f"{'='*70}")

# Sort by field count
all_forms.sort(key=lambda x: x["field_count"], reverse=True)

# Show top forms
for f in all_forms[:10]:
    print(f"  [{f['status']}] {f['filename']} — {f['field_count']} fields, path: {f['file_path']}")

# Find the actual PDF files
search_dirs = [
    PROJECT / "uploads",
    PROJECT / "Student Forms",
    PROJECT / "data",
    PROJECT / "pdf_files",
    Path(r"d:\SRC_DMS"),
    Path(r"c:\Users\as\Desktop\OCR-Installer-Final"),
]

found_pdfs = {}
for d in search_dirs:
    if d.exists():
        for root, dirs, files in os.walk(d):
            for f in files:
                if f.endswith(('.pdf', '.PDF')):
                    found_pdfs[f] = os.path.join(root, f)
                # Also check UUIDs
                for form in all_forms:
                    fp = form.get("file_path", "")
                    if fp and f == fp:
                        found_pdfs[fp] = os.path.join(root, f)

print(f"\n  PDFs found: {len(found_pdfs)}")
for name, path in list(found_pdfs.items())[:5]:
    print(f"    {name} → {path}")

# Match forms with PDFs
matched = 0
for form in all_forms:
    fp = form.get("file_path", "")
    fn = form.get("filename", "")
    
    pdf_path = None
    if fp in found_pdfs:
        pdf_path = found_pdfs[fp]
    elif fn in found_pdfs:
        pdf_path = found_pdfs[fn]
    else:
        # Search by UUID prefix
        for k, v in found_pdfs.items():
            if fp and fp in k:
                pdf_path = v
                break
            if fn and fn.replace(".pdf", "") in k:
                pdf_path = v
                break
    
    form["pdf_path"] = pdf_path
    if pdf_path:
        matched += 1

print(f"\n  Forms matched to PDFs: {matched}/{len(all_forms)}")

# Filter: forms with >= 10 fields AND a PDF
trainable = [f for f in all_forms if f["field_count"] >= 10 and f.get("pdf_path")]
print(f"  Trainable forms (>= 10 fields + PDF): {len(trainable)}")

# Also check for page images in training_data/prepared
prepared_dir = PROJECT / "training_data" / "prepared"
if prepared_dir.exists():
    images = list(prepared_dir.glob("*.png")) + list(prepared_dir.glob("*.jpg"))
    print(f"\n  Pre-rendered page images: {len(images)}")

# Check uploads directory
uploads = PROJECT / "uploads"
if uploads.exists():
    pdf_files = list(uploads.glob("*.pdf"))
    print(f"  Uploads directory PDFs: {len(pdf_files)}")
    for p in pdf_files[:5]:
        print(f"    {p.name}")

# Save the trainable data
output = {
    "total_forms": len(all_forms),
    "trainable_forms": len(trainable),
    "forms_with_pdfs": matched,
    "data": [
        {
            "form_id": f["form_id"],
            "filename": f["filename"],
            "file_path": f["file_path"],
            "pdf_path": f["pdf_path"],
            "status": f["status"],
            "field_count": f["field_count"],
            "fields": f["fields"],
        }
        for f in trainable
    ]
}

out_path = PROJECT / "training_data" / "all_verified_forms.json"
os.makedirs(out_path.parent, exist_ok=True)
with open(out_path, "w", encoding="utf-8") as fh:
    json.dump(output, fh, indent=2, ensure_ascii=False)

print(f"\n  Saved to: {out_path}")
print(f"  Total trainable: {len(trainable)} forms")
