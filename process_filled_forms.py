"""
Process Filled Forms - Auto-scan and Auto-fill
Process all PDFs in data/samples/pdfs/ and auto-fill fields
"""
import asyncio
import sys
from pathlib import Path
import requests
import json
from typing import Dict, Any, List

sys.path.insert(0, str(Path(__file__).parent))

from backend.ocr import get_ocr_provider
from backend.utils.file_handler import load_all_pdf_pages
from backend.utils.form_parser import parse_form_text
from backend.utils.ai_form_parser import AIFormParser


async def process_form_with_craft_trocr(pdf_path: str, api_url: str = "http://localhost:8000") -> Dict[str, Any]:
    """
    Process a form using CRAFT-TROCR and auto-fill fields
    
    Returns:
        Dictionary with extraction results and auto-filled fields
    """
    print(f"\n{'='*60}")
    print(f"Processing: {Path(pdf_path).name}")
    print(f"{'='*60}")
    
    try:
        # Load PDF pages
        pages = load_all_pdf_pages(pdf_path)
        if not pages:
            print(f"❌ Failed to load PDF")
            return None
        
        print(f"✅ Loaded {len(pages)} pages")
        
        # Use CRAFT-TROCR provider
        try:
            provider = get_ocr_provider('craft-trocr')
            print(f"✅ Using CRAFT-TROCR provider")
        except Exception as e:
            print(f"⚠️  CRAFT-TROCR not available: {e}")
            print(f"   Trying Tesseract as fallback...")
            provider = get_ocr_provider('tesseract')
        
        # Process first page (or all pages)
        all_text = []
        structured_data = {}
        
        for i, page in enumerate(pages[:4]):  # Process first 4 pages
            print(f"\n📄 Processing page {i+1}...")
            
            # Extract text
            ocr_result = await provider.extract_text(page)
            page_text = ocr_result.get('raw_text', '')
            all_text.append(page_text)
            
            print(f"   Extracted {len(page_text)} characters")
            print(f"   Confidence: {ocr_result.get('confidence', 0):.1f}%")
            
            # Parse structured data from first page
            if i == 0 and page_text:
                # Use form parser
                parsed = parse_form_text(page_text)
                if parsed:
                    structured_data.update(parsed)
                    print(f"   Parsed {len(parsed)} fields")
        
        # Combine all text
        full_text = "\n\n".join(all_text)
        
        # Use AI form parser for additional extraction
        ai_parser = AIFormParser()
        if ocr_result.get('structured_data'):
            ai_parsed = ai_parser.parse_from_ai_result(ocr_result)
            structured_data.update(ai_parsed)
        
        # Also parse from raw text
        text_parsed = ai_parser.parse_from_text(full_text)
        structured_data.update(text_parsed)
        
        # Prepare result
        result = {
            'filename': Path(pdf_path).name,
            'raw_text': full_text,
            'structured_data': structured_data,
            'confidence': ocr_result.get('confidence', 0),
            'provider': ocr_result.get('provider', 'craft-trocr'),
            'pages_processed': len(pages),
            'fields_extracted': len(structured_data)
        }
        
        print(f"\n✅ Processing complete!")
        print(f"   Total text: {len(full_text)} characters")
        print(f"   Fields extracted: {len(structured_data)}")
        print(f"\n📋 Extracted Fields:")
        for key, value in list(structured_data.items())[:10]:  # Show first 10
            if value:
                print(f"   {key}: {value[:50]}")
        if len(structured_data) > 10:
            print(f"   ... and {len(structured_data) - 10} more fields")
        
        return result
    
    except Exception as e:
        print(f"❌ Error processing form: {e}")
        import traceback
        traceback.print_exc()
        return None


async def upload_and_process_form(pdf_path: str, api_url: str = "http://localhost:8000") -> Dict[str, Any]:
    """
    Upload form via API and get auto-filled data
    """
    print(f"\n{'='*60}")
    print(f"Uploading via API: {Path(pdf_path).name}")
    print(f"{'='*60}")
    
    try:
        # Upload form
        with open(pdf_path, 'rb') as f:
            files = {'file': (Path(pdf_path).name, f, 'application/pdf')}
            data = {'ocr_provider': 'craft-trocr'}
            
            response = requests.post(
                f"{api_url}/api/upload",
                files=files,
                data=data,
                timeout=120
            )
        
        if response.status_code == 201:
            form_data = response.json()
            form_id = form_data.get('id')
            print(f"✅ Upload successful! Form ID: {form_id}")
            
            # Get form details (with extracted data)
            detail_response = requests.get(f"{api_url}/api/forms/{form_id}")
            if detail_response.status_code == 200:
                form_detail = detail_response.json()
                
                # Extract structured data
                extracted = form_detail.get('extracted_data', {})
                structured = extracted.get('structured_data', {})
                
                print(f"\n📋 Auto-filled Fields:")
                for key, value in list(structured.items())[:15]:
                    if value:
                        print(f"   {key}: {value[:60]}")
                
                return {
                    'form_id': form_id,
                    'form_data': form_detail,
                    'structured_data': structured,
                    'raw_text': extracted.get('raw_text', '')
                }
        
        print(f"❌ Upload failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return None
    
    except requests.exceptions.ConnectionError:
        print(f"⚠️  API server not running at {api_url}")
        print(f"   Start server with: python -m uvicorn backend.main:app --reload")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


async def process_all_forms(use_api: bool = True, api_url: str = "http://localhost:8000"):
    """
    Process all PDFs in data/samples/pdfs/
    """
    print("="*60)
    print("Processing All Filled Forms")
    print("="*60)
    print("\nUsing CRAFT-TROCR with best TrOCR model from HuggingFace")
    print("Auto-extracting and auto-filling form fields...")
    
    # Find PDFs
    pdf_dir = Path("data/samples/pdfs")
    if not pdf_dir.exists():
        print(f"❌ PDF directory not found: {pdf_dir}")
        return
    
    pdfs = list(pdf_dir.glob("*.pdf"))
    if not pdfs:
        print(f"❌ No PDFs found in {pdf_dir}")
        return
    
    print(f"\n📁 Found {len(pdfs)} PDF files")
    print(f"\n🎯 Processing all forms...\n")
    
    results = []
    
    for i, pdf in enumerate(pdfs, 1):
        print(f"\n{'#'*60}")
        print(f"Form {i}/{len(pdfs)}")
        print(f"{'#'*60}")
        
        if use_api:
            result = await upload_and_process_form(str(pdf), api_url)
        else:
            result = await process_form_with_craft_trocr(str(pdf))
        
        if result:
            results.append({
                'filename': Path(pdf).name,
                'result': result
            })
    
    # Summary
    print(f"\n{'='*60}")
    print("Processing Summary")
    print(f"{'='*60}")
    print(f"✅ Successfully processed: {len(results)}/{len(pdfs)} forms")
    
    if results:
        total_fields = sum(len(r['result'].get('structured_data', {})) for r in results)
        avg_fields = total_fields / len(results)
        print(f"📊 Average fields per form: {avg_fields:.1f}")
        print(f"📊 Total fields extracted: {total_fields}")
        
        print(f"\n📋 Forms ready for verification:")
        for r in results:
            form_id = r['result'].get('form_id', 'N/A')
            fields = len(r['result'].get('structured_data', {}))
            print(f"   {r['filename']}: Form ID {form_id}, {fields} fields")
            if form_id != 'N/A':
                print(f"      View at: http://localhost:5173/forms/{form_id}")
    
    print(f"\n💡 Next Steps:")
    print(f"1. Review forms in the UI")
    print(f"2. Verify and correct extracted fields")
    print(f"3. System will learn from your corrections")
    print(f"4. Train model after 50+ verified forms")
    
    return results


async def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Process filled forms with CRAFT-TROCR")
    parser.add_argument("--no-api", action="store_true", help="Process directly without API")
    parser.add_argument("--api-url", default="http://localhost:8000", help="API URL")
    
    args = parser.parse_args()
    
    await process_all_forms(use_api=not args.no_api, api_url=args.api_url)


if __name__ == "__main__":
    asyncio.run(main())
