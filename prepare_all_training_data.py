"""
Unified Training Data Preparation for OCR Model Training

Collects verified admission form data from ALL sources:
1. SQLite database (verified forms with 90+ fields)
2. verified_samples.json (raw OCR text + verified field values)
3. Student Forms/ directory (50 named PDF forms)
4. uploads/ directory (1000+ uploaded PDFs)

Produces training datasets for:
- TrOCR fine-tuning (image → text pairs)
- Field extraction training (raw OCR → structured fields)
- Evaluation benchmarking
"""

import json
import os
import sys
import argparse
import random
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# --- Conditional imports with graceful fallback ---
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    from sqlalchemy.orm import Session
    from backend.database import get_db, AdmissionForm, FormStatus, engine, SessionLocal
    DB_AVAILABLE = True
except Exception:
    DB_AVAILABLE = False


# ============================================================
# Constants
# ============================================================
PROJECT_ROOT = Path(__file__).parent
STUDENT_FORMS_DIR = PROJECT_ROOT / "Student Forms"
UPLOADS_DIR = PROJECT_ROOT / "uploads"
VERIFIED_SAMPLES_PATH = PROJECT_ROOT / "training_data" / "google_ocr" / "verified_samples.json"
OUTPUT_DIR = PROJECT_ROOT / "training_data" / "prepared"

# All form fields from the AdmissionForm model (90+ fields)
FORM_FIELDS = [
    # Page 1: Academic & Admission Details
    "academic_session", "course", "admission_category", "admission_category_other",
    "du_portal_form_number", "cuet_score", "college_roll_no", "date_of_admission",
    # Page 1: Personal Details
    "first_name", "middle_name", "surname", "student_name", "gender",
    "date_of_birth", "category", "nationality", "religion", "aadhar_number",
    "blood_group", "below_poverty_line", "minority_category",
    # Page 1: Address Details
    "permanent_address_line1", "permanent_address_line2", "permanent_address_line3",
    "permanent_state", "permanent_pincode", "permanent_address",
    "correspondence_address_line1", "correspondence_address_line2",
    "correspondence_address_line3", "correspondence_state", "correspondence_pincode",
    "correspondence_address",
    # Contact Details
    "phone_number", "alternate_phone", "email",
    "emergency_contact_name", "emergency_contact_phone",
    # Parent Names
    "mother_name", "father_name",
    # CUET Marks
    "cuet_subject_1", "cuet_total_score_1", "cuet_score_obtained_1",
    "cuet_subject_2", "cuet_total_score_2", "cuet_score_obtained_2",
    "cuet_subject_3", "cuet_total_score_3", "cuet_score_obtained_3",
    "cuet_subject_4", "cuet_total_score_4", "cuet_score_obtained_4",
    "cuet_subject_5", "cuet_total_score_5", "cuet_score_obtained_5",
    "cuet_subject_6", "cuet_total_score_6", "cuet_score_obtained_6",
    "cuet_total_score",
    # Qualifying Examination
    "twelfth_year", "twelfth_board", "twelfth_roll_number", "twelfth_institution",
    "hindi_studied_upto", "annual_income",
    # Mother's Details
    "mother_occupation", "mother_designation", "mother_organization",
    "mother_email", "mother_mobile",
    # Father's Details
    "father_occupation", "father_designation", "father_organization",
    "father_email", "father_mobile",
    # Guardian's Details
    "guardian_name", "guardian_residential_address", "guardian_organization",
    "guardian_email", "guardian_mobile", "guardian_relation",
    # Other Information
    "du_enrollment_number", "hindi_medium_preference",
    # Category Certificate
    "category_certificate_authority", "category_certificate_number",
    "category_certificate_date", "disability_percentage", "disability_type",
    "udid_number",
    # Educational Qualifications (legacy)
    "tenth_board", "tenth_year", "tenth_percentage", "tenth_school",
    "twelfth_percentage", "twelfth_school",
]


# ============================================================
# PDF → Image Conversion
# ============================================================
def pdf_to_images(pdf_path: str, dpi: int = 200) -> List['Image.Image']:
    """Convert a PDF file to a list of PIL Images using PyMuPDF."""
    if not PYMUPDF_AVAILABLE:
        print(f"  ⚠ PyMuPDF not installed, skipping {pdf_path}")
        return []
    if not PIL_AVAILABLE:
        print(f"  ⚠ Pillow not installed, skipping {pdf_path}")
        return []

    images = []
    try:
        doc = fitz.open(pdf_path)
        for page_num in range(len(doc)):
            page = doc[page_num]
            # Render at specified DPI
            zoom = dpi / 72.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            images.append(img)
        doc.close()
    except Exception as e:
        print(f"  ✗ Error converting {pdf_path}: {e}")
    return images


# ============================================================
# Data Source 1: SQLite Database
# ============================================================
def load_from_database(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Load verified forms from the SQLite database."""
    if not DB_AVAILABLE:
        print("  ⚠ Database not available, skipping DB source")
        return []

    records = []
    db = SessionLocal()
    try:
        query = db.query(AdmissionForm).filter(
            AdmissionForm.status == FormStatus.VERIFIED
        )
        if limit:
            query = query.limit(limit)
        forms = query.all()

        for form in forms:
            fields = {}
            non_empty = 0
            for field in FORM_FIELDS:
                val = getattr(form, field, None)
                if val and str(val).strip():
                    fields[field] = str(val).strip()
                    non_empty += 1

            if non_empty >= 3:  # At least 3 fields must be populated
                record = {
                    "source": "database",
                    "form_id": form.id,
                    "filename": form.filename,
                    "file_path": form.file_path,
                    "ocr_provider": form.ocr_provider,
                    "fields": fields,
                    "field_count": non_empty,
                    "extracted_data": form.extracted_data,
                }
                records.append(record)

        print(f"  ✓ Loaded {len(records)} verified forms from database ({len(forms)} total queried)")
    except Exception as e:
        print(f"  ✗ Error loading from database: {e}")
    finally:
        db.close()

    return records


# ============================================================
# Data Source 2: verified_samples.json
# ============================================================
def load_from_verified_json() -> List[Dict[str, Any]]:
    """Load verified samples from JSON file."""
    if not VERIFIED_SAMPLES_PATH.exists():
        print(f"  ⚠ {VERIFIED_SAMPLES_PATH} not found, skipping")
        return []

    records = []
    try:
        with open(VERIFIED_SAMPLES_PATH, "r", encoding="utf-8") as f:
            samples = json.load(f)

        for sample in samples:
            fields = {}
            raw_text = ""

            # Extract verified fields
            if "verified_fields" in sample:
                for key, val in sample["verified_fields"].items():
                    if val and str(val).strip():
                        fields[key] = str(val).strip()

            # Extract raw OCR text
            if "raw_ocr_text" in sample:
                raw_text = sample["raw_ocr_text"]
            elif "extracted_text" in sample:
                raw_text = sample["extracted_text"]

            if fields or raw_text:
                records.append({
                    "source": "verified_json",
                    "form_id": sample.get("form_id", "unknown"),
                    "filename": sample.get("filename", ""),
                    "fields": fields,
                    "field_count": len(fields),
                    "raw_ocr_text": raw_text,
                    "confidence": sample.get("confidence", 0),
                })

        print(f"  ✓ Loaded {len(records)} samples from verified_samples.json")
    except Exception as e:
        print(f"  ✗ Error loading verified_samples.json: {e}")

    return records


# ============================================================
# Data Source 3: Student Forms (PDFs)
# ============================================================
def load_student_forms(max_forms: Optional[int] = None) -> List[Dict[str, Any]]:
    """Load student form PDFs and convert to images."""
    if not STUDENT_FORMS_DIR.exists():
        print(f"  ⚠ {STUDENT_FORMS_DIR} not found, skipping")
        return []

    records = []
    pdf_files = sorted(STUDENT_FORMS_DIR.glob("*.pdf"))
    if max_forms:
        pdf_files = pdf_files[:max_forms]

    for pdf_file in pdf_files:
        # Extract student name from filename: UN-XX-XXXXXXXXX-NAME.pdf
        name_parts = pdf_file.stem.split("-")
        student_name = name_parts[-1].strip() if len(name_parts) >= 4 else pdf_file.stem

        records.append({
            "source": "student_forms",
            "filename": pdf_file.name,
            "file_path": str(pdf_file),
            "student_name": student_name,
            "form_number": name_parts[1] if len(name_parts) >= 2 else "",
        })

    print(f"  ✓ Found {len(records)} student form PDFs")
    return records


# ============================================================
# Dataset Builder
# ============================================================
def build_training_dataset(
    db_records: List[Dict],
    json_records: List[Dict],
    student_forms: List[Dict],
    output_dir: Path,
    convert_images: bool = True,
    dpi: int = 200,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
) -> Dict[str, Any]:
    """
    Build unified training dataset from all sources.
    
    Creates:
    - training_data.json: All records with fields, metadata, and image paths
    - images/: Converted page images from PDFs
    - field_extraction/: Raw OCR text → structured fields pairs
    - splits.json: Train/val/test split assignments
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    images_dir = output_dir / "images"
    images_dir.mkdir(exist_ok=True)

    all_records = []
    stats = {
        "total_records": 0,
        "from_database": len(db_records),
        "from_verified_json": len(json_records),
        "from_student_forms": len(student_forms),
        "total_fields_extracted": 0,
        "total_images_created": 0,
        "field_coverage": {},
    }

    # --- Process DB records ---
    for rec in db_records:
        entry = {
            "id": f"db_{rec['form_id']}",
            "source": "database",
            "fields": rec["fields"],
            "field_count": rec["field_count"],
            "images": [],
        }

        # Convert PDF to images if available
        if convert_images and rec.get("file_path"):
            pdf_path = PROJECT_ROOT / rec["file_path"]
            if not pdf_path.exists():
                # Try uploads directory
                pdf_path = UPLOADS_DIR / os.path.basename(rec["file_path"])
            if pdf_path.exists() and pdf_path.stat().st_size > 100:
                page_images = pdf_to_images(str(pdf_path), dpi=dpi)
                for i, img in enumerate(page_images):
                    img_name = f"db_{rec['form_id']}_page_{i+1}.png"
                    img_path = images_dir / img_name
                    img.save(str(img_path))
                    entry["images"].append(str(img_path))
                    stats["total_images_created"] += 1

        # Track raw OCR text from extracted_data
        if rec.get("extracted_data"):
            if isinstance(rec["extracted_data"], dict):
                entry["raw_ocr_text"] = rec["extracted_data"].get("raw_text", "")
            elif isinstance(rec["extracted_data"], str):
                entry["raw_ocr_text"] = rec["extracted_data"]

        all_records.append(entry)
        stats["total_fields_extracted"] += rec["field_count"]

    # --- Process verified JSON records ---
    for rec in json_records:
        entry = {
            "id": f"json_{rec['form_id']}",
            "source": "verified_json",
            "fields": rec["fields"],
            "field_count": rec["field_count"],
            "raw_ocr_text": rec.get("raw_ocr_text", ""),
            "confidence": rec.get("confidence", 0),
            "images": [],
        }

        # Try to find the matching PDF in uploads
        if rec.get("filename"):
            pdf_path = UPLOADS_DIR / rec["filename"]
            if convert_images and pdf_path.exists() and pdf_path.stat().st_size > 100:
                page_images = pdf_to_images(str(pdf_path), dpi=dpi)
                for i, img in enumerate(page_images):
                    img_name = f"json_{rec['form_id']}_page_{i+1}.png"
                    img_path = images_dir / img_name
                    img.save(str(img_path))
                    entry["images"].append(str(img_path))
                    stats["total_images_created"] += 1

        all_records.append(entry)
        stats["total_fields_extracted"] += rec["field_count"]

    # --- Process Student Form PDFs ---
    for rec in student_forms:
        entry = {
            "id": f"sf_{rec.get('form_number', '')}_{rec['student_name']}",
            "source": "student_forms",
            "filename": rec["filename"],
            "student_name": rec["student_name"],
            "fields": {},
            "images": [],
        }

        if convert_images:
            page_images = pdf_to_images(rec["file_path"], dpi=dpi)
            for i, img in enumerate(page_images):
                safe_name = rec["filename"].replace(" ", "_").replace(".pdf", "")
                img_name = f"sf_{safe_name}_page_{i+1}.png"
                img_path = images_dir / img_name
                img.save(str(img_path))
                entry["images"].append(str(img_path))
                stats["total_images_created"] += 1

        all_records.append(entry)

    # --- Calculate field coverage ---
    field_counts = {}
    for rec in all_records:
        for field in rec.get("fields", {}):
            field_counts[field] = field_counts.get(field, 0) + 1
    stats["field_coverage"] = dict(sorted(field_counts.items(), key=lambda x: -x[1]))

    # --- Create train/val/test splits ---
    random.seed(42)
    indices = list(range(len(all_records)))
    random.shuffle(indices)

    n_train = int(len(indices) * train_ratio)
    n_val = int(len(indices) * val_ratio)

    splits = {
        "train": indices[:n_train],
        "val": indices[n_train:n_train + n_val],
        "test": indices[n_train + n_val:],
    }

    for rec_idx in splits["train"]:
        if rec_idx < len(all_records):
            all_records[rec_idx]["split"] = "train"
    for rec_idx in splits["val"]:
        if rec_idx < len(all_records):
            all_records[rec_idx]["split"] = "val"
    for rec_idx in splits["test"]:
        if rec_idx < len(all_records):
            all_records[rec_idx]["split"] = "test"

    stats["total_records"] = len(all_records)
    stats["train_count"] = len(splits["train"])
    stats["val_count"] = len(splits["val"])
    stats["test_count"] = len(splits["test"])
    stats["prepared_at"] = datetime.now().isoformat()

    # --- Save outputs ---
    # Save all records
    with open(output_dir / "training_data.json", "w", encoding="utf-8") as f:
        json.dump(all_records, f, indent=2, ensure_ascii=False, default=str)

    # Save splits
    with open(output_dir / "splits.json", "w", encoding="utf-8") as f:
        json.dump(splits, f, indent=2)

    # Save stats
    with open(output_dir / "preparation_stats.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

    # Save field extraction pairs (for training the field mapper)
    field_extraction_pairs = []
    for rec in all_records:
        if rec.get("raw_ocr_text") and rec.get("fields"):
            field_extraction_pairs.append({
                "input": rec["raw_ocr_text"],
                "output": rec["fields"],
                "source": rec["source"],
            })
    if field_extraction_pairs:
        with open(output_dir / "field_extraction_pairs.json", "w", encoding="utf-8") as f:
            json.dump(field_extraction_pairs, f, indent=2, ensure_ascii=False)

    return stats


# ============================================================
# Main CLI
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description="Prepare unified training data for OCR models",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python prepare_all_training_data.py                          # Full run
  python prepare_all_training_data.py --dry-run                # Preview only
  python prepare_all_training_data.py --no-images              # Skip image conversion
  python prepare_all_training_data.py --max-db 10 --max-forms 5  # Subset
        """
    )
    parser.add_argument("--output", default=str(OUTPUT_DIR), help="Output directory")
    parser.add_argument("--dry-run", action="store_true", help="Preview data counts without writing")
    parser.add_argument("--no-images", action="store_true", help="Skip PDF→image conversion")
    parser.add_argument("--max-db", type=int, default=None, help="Max DB records to load")
    parser.add_argument("--max-forms", type=int, default=None, help="Max student forms to process")
    parser.add_argument("--dpi", type=int, default=200, help="DPI for image conversion")
    parser.add_argument("--train-ratio", type=float, default=0.70, help="Train split ratio")
    parser.add_argument("--val-ratio", type=float, default=0.15, help="Validation split ratio")

    args = parser.parse_args()

    print("=" * 70)
    print("  OCR Training Data Preparation")
    print("=" * 70)
    print()

    # --- Load data from all sources ---
    print("📂 Loading data sources...")
    print()

    print("  [1/3] Database (verified forms)...")
    db_records = load_from_database(limit=args.max_db)

    print("  [2/3] Verified samples JSON...")
    json_records = load_from_verified_json()

    print("  [3/3] Student Form PDFs...")
    student_forms = load_student_forms(max_forms=args.max_forms)

    print()
    total = len(db_records) + len(json_records) + len(student_forms)
    print(f"📊 Total records: {total}")
    print(f"   • Database:       {len(db_records)}")
    print(f"   • Verified JSON:  {len(json_records)}")
    print(f"   • Student Forms:  {len(student_forms)}")

    if args.dry_run:
        print()
        print("🔍 DRY RUN — no files written")

        # Show field coverage from loaded data
        field_counts = {}
        for rec in db_records + json_records:
            for field in rec.get("fields", {}):
                field_counts[field] = field_counts.get(field, 0) + 1

        if field_counts:
            print()
            print("📋 Field coverage (top 20):")
            for field, count in sorted(field_counts.items(), key=lambda x: -x[1])[:20]:
                bar = "█" * min(count, 30)
                print(f"   {field:40s} {count:4d}  {bar}")
        return

    # --- Build dataset ---
    print()
    output_path = Path(args.output)
    print(f"🔨 Building dataset → {output_path}")
    if not args.no_images:
        print(f"   Image DPI: {args.dpi}")
    print(f"   Splits: train={args.train_ratio:.0%} / val={args.val_ratio:.0%} / test={1-args.train_ratio-args.val_ratio:.0%}")
    print()

    stats = build_training_dataset(
        db_records=db_records,
        json_records=json_records,
        student_forms=student_forms,
        output_dir=output_path,
        convert_images=not args.no_images,
        dpi=args.dpi,
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
    )

    # --- Print summary ---
    print()
    print("=" * 70)
    print("  ✅ Dataset Preparation Complete")
    print("=" * 70)
    print(f"   Total records:    {stats['total_records']}")
    print(f"   Images created:   {stats['total_images_created']}")
    print(f"   Fields extracted:  {stats['total_fields_extracted']}")
    print(f"   Train / Val / Test: {stats['train_count']} / {stats['val_count']} / {stats['test_count']}")
    print()
    print(f"   Output directory: {output_path}")
    print(f"   training_data.json:        All records with fields + image paths")
    print(f"   field_extraction_pairs.json: OCR text → structured fields")
    print(f"   splits.json:               Train/val/test indices")
    print(f"   preparation_stats.json:    Statistics")
    print(f"   images/:                   Converted page images")


if __name__ == "__main__":
    main()
