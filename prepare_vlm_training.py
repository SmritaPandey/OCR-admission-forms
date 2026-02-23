"""
Prepare training data: Convert PDFs to page images and build
final training dataset for VLM fine-tuning.

Creates: training_data/vlm_training/
  - form_XX_page_Y.png  (page images)
  - training_manifest.json (image path + verified field JSON pairs)
"""
import json
import os
import sys
from pathlib import Path
from PIL import Image

PROJECT = Path(__file__).parent

def convert_pdfs_to_images(forms_data, output_dir, dpi=200):
    """Convert all form PDFs to page images using PyMuPDF (fitz)."""
    import fitz  # PyMuPDF — no Poppler needed
    
    os.makedirs(output_dir, exist_ok=True)
    manifest = []
    
    for i, form in enumerate(forms_data):
        pdf_path = form.get("pdf_path")
        if not pdf_path or not os.path.exists(pdf_path):
            print(f"  [{i+1}] SKIP — no PDF: {form.get('filename')}")
            continue
        
        fields = form.get("fields", {})
        if len(fields) < 5:
            print(f"  [{i+1}] SKIP — too few fields ({len(fields)}): {form.get('filename')}")
            continue
        
        form_id = form.get("form_id", i)
        
        try:
            doc = fitz.open(pdf_path)
            page_paths = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                # Render at specified DPI
                zoom = dpi / 72.0
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat)
                
                img_name = f"form_{form_id:03d}_page_{page_num + 1}.png"
                img_path = os.path.join(output_dir, img_name)
                
                # Convert to PIL for resizing
                page_img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                
                # Resize if too large (keep under 1280px width for VLM)
                w, h = page_img.size
                if w > 1280:
                    ratio = 1280 / w
                    page_img = page_img.resize((1280, int(h * ratio)), Image.LANCZOS)
                
                page_img.save(img_path, "PNG", optimize=True)
                page_paths.append(img_path)
            
            doc.close()
            
            manifest.append({
                "form_id": form_id,
                "filename": form.get("filename"),
                "pdf_path": pdf_path,
                "page_images": page_paths,
                "num_pages": len(page_paths),
                "field_count": len(fields),
                "fields": fields,
                "status": form.get("status"),
            })
            
            print(f"  [{i+1}] ✅ {form.get('filename')} — {len(page_paths)} pages, {len(fields)} fields")
            
        except Exception as e:
            print(f"  [{i+1}] ❌ Error processing {form.get('filename')}: {e}")
            continue
    
    return manifest



def split_fields_by_page(fields):
    """
    Split fields into page-specific groups based on which page they appear on.
    This helps the VLM learn which fields come from which page.
    """
    page1_fields = {}
    page2_fields = {}
    page3_fields = {}
    page4_fields = {}
    
    # Page 1: Academic details, personal info, address, CUET marks
    page1_keys = {
        "academic_session", "course", "admission_category", "admission_category_other",
        "du_portal_form_number", "cuet_score", "college_roll_no", "date_of_admission",
        "first_name", "middle_name", "surname", "student_name",
        "gender", "date_of_birth", "category", "nationality", "religion",
        "aadhar_number", "blood_group", "below_poverty_line", "minority_category",
        "permanent_address", "permanent_address_line1", "permanent_address_line2",
        "permanent_address_line3", "permanent_state", "permanent_pincode",
        "correspondence_address", "correspondence_address_line1", "correspondence_address_line2",
        "correspondence_address_line3", "correspondence_state", "correspondence_pincode",
        "phone_number", "alternate_phone", "email",
        "emergency_contact_name", "emergency_contact_phone",
        "mother_name", "father_name",
        "cuet_subject_1", "cuet_total_score_1", "cuet_score_obtained_1",
        "cuet_subject_2", "cuet_total_score_2", "cuet_score_obtained_2",
        "cuet_subject_3", "cuet_total_score_3", "cuet_score_obtained_3",
        "cuet_subject_4", "cuet_total_score_4", "cuet_score_obtained_4",
        "cuet_subject_5", "cuet_total_score_5", "cuet_score_obtained_5",
        "cuet_subject_6", "cuet_total_score_6", "cuet_score_obtained_6",
        "cuet_total_score",
    }
    
    # Page 2: Qualifying exam, parent/guardian details
    page2_keys = {
        "twelfth_year", "twelfth_board", "twelfth_roll_number", "twelfth_institution",
        "hindi_studied_upto", "annual_income",
        "mother_occupation", "mother_designation", "mother_organization",
        "mother_email", "mother_mobile", "mother_landline_code", "mother_landline", "mother_phone",
        "father_occupation", "father_designation", "father_organization",
        "father_email", "father_mobile", "father_landline_code", "father_landline", "father_phone",
        "guardian_name", "guardian_residential_address", "guardian_organization",
        "guardian_email", "guardian_mobile", "guardian_landline_code", "guardian_landline",
        "guardian_relation", "guardian_phone",
        "du_enrollment_number", "hindi_medium_preference",
        "category_certificate_authority", "category_certificate_number",
        "category_certificate_date", "disability_percentage", "disability_type", "udid_number",
    }
    
    # Page 4: Document checklist
    page4_keys = {
        "doc_admission_form", "doc_undertaking_ragging", "doc_photographs",
        "doc_cuet_scorecard", "doc_class_xii_marksheet", "doc_class_x_certificate",
        "doc_class_xii_certificate", "doc_character_certificate", "doc_transfer_certificate",
        "doc_hindi_certificate", "doc_caste_certificate", "doc_sports_eca",
        "doc_originals", "doc_photo_id",
    }
    
    for key, val in fields.items():
        if key in page1_keys:
            page1_fields[key] = val
        elif key in page2_keys:
            page2_fields[key] = val
        elif key in page4_keys:
            page4_fields[key] = val
        else:
            page3_fields[key] = val  # Fallback
    
    return {
        1: page1_fields,
        2: page2_fields,
        3: page3_fields,
        4: page4_fields,
    }


def build_training_samples(manifest, output_dir):
    """
    Build per-page training samples: (page_image, page_fields) pairs.
    This is the key training data format for VLM fine-tuning.
    """
    samples = []
    
    for form in manifest:
        page_images = form["page_images"]
        fields = form["fields"]
        
        # Split fields into page-specific groups
        page_fields = split_fields_by_page(fields)
        
        for page_num, page_img in enumerate(page_images, 1):
            if page_num > 4:
                break  # Forms have max 4 pages
            
            pf = page_fields.get(page_num, {})
            if len(pf) < 3:
                continue  # Skip pages with very few fields
            
            samples.append({
                "image_path": page_img,
                "page_number": page_num,
                "form_id": form["form_id"],
                "filename": form["filename"],
                "fields": pf,
                "field_count": len(pf),
            })
    
    # Save manifest
    manifest_path = os.path.join(output_dir, "training_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump({
            "total_samples": len(samples),
            "total_forms": len(manifest),
            "samples": samples,
        }, f, indent=2, ensure_ascii=False)
    
    return samples


def main():
    print("=" * 70)
    print("  📦 Preparing VLM Training Data from Verified Admission Forms")
    print("=" * 70)
    
    # Load extracted forms
    forms_path = PROJECT / "training_data" / "all_verified_forms.json"
    with open(forms_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    forms = data["data"]
    print(f"\n  Total trainable forms: {len(forms)}")
    
    # Convert PDFs to images
    output_dir = str(PROJECT / "training_data" / "vlm_training")
    print(f"\n  Converting PDFs to page images...")
    manifest = convert_pdfs_to_images(forms, output_dir, dpi=200)
    
    print(f"\n  ✅ Converted {len(manifest)} forms successfully")
    
    # Build training samples
    print(f"\n  Building per-page training samples...")
    samples = build_training_samples(manifest, output_dir)
    
    # Stats
    page_counts = {}
    for s in samples:
        p = s["page_number"]
        page_counts[p] = page_counts.get(p, 0) + 1
    
    print(f"\n{'='*70}")
    print(f"  TRAINING DATA READY")
    print(f"{'='*70}")
    print(f"  Total forms processed: {len(manifest)}")
    print(f"  Total training samples: {len(samples)}")
    print(f"  Per page: {page_counts}")
    avg_fields = sum(s['field_count'] for s in samples) / max(len(samples), 1)
    print(f"  Avg fields per sample: {avg_fields:.1f}")
    print(f"  Output: {output_dir}")
    print(f"  Manifest: {output_dir}/training_manifest.json")


if __name__ == "__main__":
    main()
