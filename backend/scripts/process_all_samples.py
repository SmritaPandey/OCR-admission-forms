#!/usr/bin/env python3
"""
Process all PDF files from data/samples/pdfs/ using Google Vision
"""
import sys
import asyncio
from pathlib import Path
from typing import List

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.database import SessionLocal, AdmissionForm, FormStatus
from backend.utils.file_handler import save_uploaded_file, load_all_pdf_pages
from backend.ocr import get_ocr_provider
from backend.config import settings
from backend.api.routes.students import get_or_create_student_profile
import os

async def process_pdf_file(pdf_path: Path, ocr_provider_name: str = "google-vision"):
    """Process a single PDF file"""
    db = SessionLocal()
    
    try:
        filename = pdf_path.name
        print(f"\n📄 Processing: {filename}")
        
        # Load all pages from PDF
        pages = load_all_pdf_pages(str(pdf_path))
        if not pages:
            print(f"   ❌ Failed to load pages from {filename}")
            return None
        
        print(f"   📑 Loaded {len(pages)} pages")
        
        # Get OCR provider
        try:
            provider = get_ocr_provider(ocr_provider_name)
            print(f"   🔍 Using OCR provider: {provider.get_provider_name()}")
        except Exception as e:
            print(f"   ❌ Failed to get OCR provider: {e}")
            return None
        
        # Process first 4 pages as the form (rest are supporting documents)
        form_pages = pages[:4] if len(pages) >= 4 else pages
        
        # Combine pages for OCR processing (Google Vision can handle multiple pages)
        from PIL import Image
        import io
        
        # Process pages (we'll process each page and combine results)
        all_raw_text = []
        all_structured_data = {}
        page_results = []
        total_confidence = 0.0
        
        for page_num, page_image in enumerate(form_pages, 1):
            print(f"   ⏳ Processing page {page_num}/{len(form_pages)}...")
            try:
                result = await provider.extract_text(page_image)
                
                if result.get("raw_text"):
                    all_raw_text.append(result["raw_text"])
                
                # Merge structured data
                if result.get("structured_data"):
                    structured = result.get("structured_data")
                    if isinstance(structured, dict):
                        if structured.get("fields"):
                            all_structured_data.update(structured["fields"])
                        else:
                            all_structured_data.update(structured)
                
                page_confidence = result.get("confidence", 0.0)
                total_confidence += page_confidence
                
                page_results.append({
                    "page": page_num,
                    "confidence": page_confidence,
                    "provider": result.get("provider", ocr_provider_name),
                    "word_count": len(result.get("raw_text", "").split())
                })
                
            except Exception as e:
                print(f"   ⚠️  Error processing page {page_num}: {e}")
                continue
        
        # Calculate average confidence
        avg_confidence = total_confidence / len(form_pages) if form_pages else 0.0
        
        # Combine raw text
        combined_raw_text = "\n\n--- Page {page_num} ---\n\n".join([
            f"--- Page {i+1} ---\n{text}" for i, text in enumerate(all_raw_text)
        ]) if all_raw_text else ""
        
        print(f"   ✅ Extracted {len(combined_raw_text)} characters, confidence: {avg_confidence:.1f}%")
        print(f"   📊 Structured fields: {len(all_structured_data)}")
        
        # Save file to upload directory (copy the PDF)
        from shutil import copy2
        upload_dir = Path(settings.UPLOAD_DIR).resolve()
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        dest_path = upload_dir / filename
        copy2(pdf_path, dest_path)
        relative_path = os.path.relpath(dest_path, upload_dir)
        
        # Create form record
        form = AdmissionForm(
            filename=filename,
            file_path=relative_path,
            ocr_provider=ocr_provider_name,
            status=FormStatus.EXTRACTED,
            extracted_data={
                "raw_text": combined_raw_text,
                "confidence": round(avg_confidence, 2),
                "structured_data": all_structured_data if all_structured_data else None,
                "pages_processed": len(form_pages),
                "total_pages": len(pages),
                "page_results": page_results,
                "provider": ocr_provider_name
            }
        )
        
        db.add(form)
        db.commit()
        db.refresh(form)
        
        print(f"   ✅ Saved form ID: {form.id}")
        
        # Don't try to auto-link to student profile here - let the frontend do it
        # The structured_data from Google Vision doesn't reliably extract student names
        # It will be handled during form verification/editing
        
        return form.id
        
    except Exception as e:
        print(f"   ❌ Error processing {pdf_path.name}: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return None
    finally:
        db.close()

async def process_all_samples(ocr_provider: str = "google-vision"):
    """Process all PDF files in data/samples/pdfs/"""
    samples_dir = project_root / "data" / "samples" / "pdfs"
    
    if not samples_dir.exists():
        print(f"❌ Samples directory not found: {samples_dir}")
        return
    
    pdf_files = list(samples_dir.glob("*.pdf"))
    
    if not pdf_files:
        print(f"❌ No PDF files found in {samples_dir}")
        return
    
    print(f"📚 Found {len(pdf_files)} PDF files to process")
    print(f"🔍 Using OCR provider: {ocr_provider}\n")
    
    results = []
    for pdf_path in sorted(pdf_files):
        form_id = await process_pdf_file(pdf_path, ocr_provider)
        results.append((pdf_path.name, form_id))
        # Small delay between files
        await asyncio.sleep(0.5)
    
    # Summary
    print("\n" + "="*60)
    print("📊 Processing Summary")
    print("="*60)
    successful = [r for r in results if r[1] is not None]
    failed = [r for r in results if r[1] is None]
    
    print(f"✅ Successfully processed: {len(successful)}/{len(results)}")
    if successful:
        print("\nSuccessful:")
        for filename, form_id in successful:
            print(f"  - {filename} → Form ID: {form_id}")
    
    if failed:
        print(f"\n❌ Failed: {len(failed)}")
        for filename, _ in failed:
            print(f"  - {filename}")

if __name__ == "__main__":
    ocr_provider = sys.argv[1] if len(sys.argv) > 1 else "google-vision"
    asyncio.run(process_all_samples(ocr_provider))

