"""
Simple form processing - Direct processing without API
Processes forms directly and shows results
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.ocr import get_ocr_provider
from backend.utils.file_handler import load_all_pdf_pages
from backend.utils.form_parser import parse_form_text
from backend.utils.ai_form_parser import AIFormParser


async def process_form_direct(pdf_path: str):
    """Process a form directly using OCR"""
    print(f"\n{'='*60}")
    print(f"Processing: {Path(pdf_path).name}")
    print(f"{'='*60}")
    
    try:
        # Load PDF
        pages = load_all_pdf_pages(pdf_path)
        if not pages:
            print(f"❌ Failed to load PDF")
            return None
        
        print(f"✅ Loaded {len(pages)} pages")
        
        # Try CRAFT-TROCR, fallback to Tesseract
        try:
            provider = get_ocr_provider('craft-trocr')
            print(f"✅ Using CRAFT-TROCR")
        except Exception as e:
            print(f"⚠️  CRAFT-TROCR not available: {e}")
            print(f"   Using Tesseract as fallback...")
            provider = get_ocr_provider('tesseract')
        
        # Process first page
        page = pages[0]
        print(f"📄 Extracting text from page 1...")
        
        ocr_result = await provider.extract_text(page)
        raw_text = ocr_result.get('raw_text', '')
        
        print(f"✅ Extracted {len(raw_text)} characters")
        print(f"   Confidence: {ocr_result.get('confidence', 0):.1f}%")
        
        # Parse fields
        if raw_text:
            print(f"\n📋 Parsing fields...")
            structured = parse_form_text(raw_text)
            
            # Also use AI parser
            ai_parser = AIFormParser()
            ai_parsed = ai_parser.parse_from_text(raw_text)
            structured.update(ai_parsed)
            
            print(f"✅ Extracted {len(structured)} fields")
            
            # Show extracted fields
            if structured:
                print(f"\n📝 Auto-filled Fields:")
                for key, value in list(structured.items())[:15]:
                    if value:
                        print(f"   {key}: {value[:60]}")
                if len(structured) > 15:
                    print(f"   ... and {len(structured) - 15} more fields")
            
            return {
                'filename': Path(pdf_path).name,
                'raw_text': raw_text[:200] + "..." if len(raw_text) > 200 else raw_text,
                'fields': structured,
                'field_count': len(structured)
            }
        else:
            print(f"⚠️  No text extracted")
            return None
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


async def main():
    """Process all forms"""
    print("="*60)
    print("Processing All Filled Forms")
    print("="*60)
    print("\nUsing CRAFT-TROCR with best TrOCR model")
    print("Auto-extracting and auto-filling form fields...\n")
    
    # Find PDFs
    pdf_dir = Path("data/samples/pdfs")
    pdfs = list(pdf_dir.glob("*.pdf"))
    
    print(f"📁 Found {len(pdfs)} PDF files\n")
    
    results = []
    for i, pdf in enumerate(pdfs, 1):
        print(f"\n{'#'*60}")
        print(f"Form {i}/{len(pdfs)}")
        print(f"{'#'*60}")
        
        result = await process_form_direct(str(pdf))
        if result:
            results.append(result)
    
    # Summary
    print(f"\n{'='*60}")
    print("Processing Summary")
    print(f"{'='*60}")
    print(f"✅ Successfully processed: {len(results)}/{len(pdfs)} forms")
    
    if results:
        total_fields = sum(r['field_count'] for r in results)
        avg_fields = total_fields / len(results)
        print(f"📊 Average fields per form: {avg_fields:.1f}")
        print(f"📊 Total fields extracted: {total_fields}")
        
        print(f"\n📋 Forms processed:")
        for r in results:
            print(f"   ✅ {r['filename']}: {r['field_count']} fields")
    
    print(f"\n💡 Next: Upload these forms via API or UI for verification")
    return results


if __name__ == "__main__":
    asyncio.run(main())
