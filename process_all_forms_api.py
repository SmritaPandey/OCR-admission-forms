"""
Process all forms via API - Works with any available OCR provider
"""
import requests
import json
from pathlib import Path
import time


def upload_form(pdf_path: str, api_url: str = "http://localhost:8000", ocr_provider: str = None):
    """Upload and process a form via API"""
    print(f"\n{'='*60}")
    print(f"Processing: {Path(pdf_path).name}")
    print(f"{'='*60}")
    
    try:
        with open(pdf_path, 'rb') as f:
            files = {'file': (Path(pdf_path).name, f, 'application/pdf')}
            data = {}
            if ocr_provider:
                data['ocr_provider'] = ocr_provider
            
            print(f"📤 Uploading to API...")
            response = requests.post(
                f"{api_url}/api/upload",
                files=files,
                data=data,
                timeout=180
            )
        
        if response.status_code == 201:
            form_data = response.json()
            form_id = form_data.get('id')
            print(f"✅ Upload successful! Form ID: {form_id}")
            
            # Wait a bit for processing
            time.sleep(2)
            
            # Get form details with extracted data
            print(f"📥 Fetching extracted data...")
            detail_response = requests.get(f"{api_url}/api/forms/{form_id}")
            
            if detail_response.status_code == 200:
                form_detail = detail_response.json()
                
                # Get structured data
                extracted = form_detail.get('extracted_data', {})
                structured = extracted.get('structured_data', {})
                raw_text = extracted.get('raw_text', '')
                
                print(f"✅ Extraction complete!")
                print(f"   Provider: {extracted.get('provider', 'unknown')}")
                print(f"   Confidence: {extracted.get('confidence', 0):.1f}%")
                print(f"   Text length: {len(raw_text)} chars")
                print(f"   Fields extracted: {len(structured)}")
                
                if structured:
                    print(f"\n📋 Auto-filled Fields:")
                    count = 0
                    for key, value in structured.items():
                        if value and count < 10:
                            print(f"   {key}: {value[:60]}")
                            count += 1
                    if len(structured) > 10:
                        print(f"   ... and {len(structured) - 10} more fields")
                
                return {
                    'form_id': form_id,
                    'filename': Path(pdf_path).name,
                    'fields': structured,
                    'field_count': len(structured),
                    'confidence': extracted.get('confidence', 0)
                }
            else:
                print(f"⚠️  Could not fetch form details: {detail_response.status_code}")
                return {'form_id': form_id, 'filename': Path(pdf_path).name}
        else:
            print(f"❌ Upload failed: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return None
    
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to API at {api_url}")
        print(f"   Make sure backend is running: python3 -m uvicorn backend.main:app --reload")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def get_available_providers(api_url: str = "http://localhost:8000"):
    """Get list of available OCR providers"""
    try:
        response = requests.get(f"{api_url}/api/providers", timeout=10)
        if response.status_code == 200:
            data = response.json()
            providers = data.get('providers', [])
            default = data.get('default', 'tesseract')
            return providers, default
    except:
        pass
    return [], 'tesseract'


def main():
    """Process all forms"""
    print("="*60)
    print("Processing All Filled Forms via API")
    print("="*60)
    
    api_url = "http://localhost:8000"
    
    # Check API availability
    print(f"\n🔍 Checking API at {api_url}...")
    try:
        response = requests.get(f"{api_url}/health", timeout=5)
        if response.status_code == 200:
            print(f"✅ API is running")
        else:
            print(f"⚠️  API responded with status {response.status_code}")
    except:
        print(f"❌ API not available at {api_url}")
        print(f"   Please start backend: python3 -m uvicorn backend.main:app --reload")
        return
    
    # Get available providers
    providers, default = get_available_providers(api_url)
    
    # Prefer Ollama if available (best for handwritten), otherwise use first available
    if 'ollama' in providers:
        ocr_provider = 'ollama'
        print(f"\n📋 Available OCR providers: {', '.join(providers)}")
        print(f"   Using: Ollama (best for handwritten forms)")
    elif providers:
        ocr_provider = providers[0]
        print(f"\n📋 Available OCR providers: {', '.join(providers)}")
        print(f"   Using: {ocr_provider}")
    else:
        ocr_provider = None  # Use default from server
        print(f"\n📋 Using server default provider")
    
    # Find PDFs
    pdf_dir = Path("data/samples/pdfs")
    pdfs = list(pdf_dir.glob("*.pdf"))
    
    if not pdfs:
        print(f"\n❌ No PDFs found in {pdf_dir}")
        return
    
    print(f"\n📁 Found {len(pdfs)} PDF files")
    print(f"\n🎯 Processing all forms...\n")
    
    results = []
    for i, pdf in enumerate(pdfs, 1):
        print(f"\n{'#'*60}")
        print(f"Form {i}/{len(pdfs)}")
        print(f"{'#'*60}")
        
        result = upload_form(str(pdf), api_url, ocr_provider)
        if result:
            results.append(result)
        
        # Small delay between uploads
        if i < len(pdfs):
            time.sleep(1)
    
    # Summary
    print(f"\n{'='*60}")
    print("Processing Summary")
    print(f"{'='*60}")
    print(f"✅ Successfully processed: {len(results)}/{len(pdfs)} forms")
    
    if results:
        total_fields = sum(r.get('field_count', 0) for r in results)
        avg_fields = total_fields / len(results) if results else 0
        avg_confidence = sum(r.get('confidence', 0) for r in results) / len(results) if results else 0
        
        print(f"📊 Average fields per form: {avg_fields:.1f}")
        print(f"📊 Total fields extracted: {total_fields}")
        print(f"📊 Average confidence: {avg_confidence:.1f}%")
        
        print(f"\n📋 Forms ready for verification:")
        for r in results:
            form_id = r.get('form_id', 'N/A')
            fields = r.get('field_count', 0)
            conf = r.get('confidence', 0)
            print(f"   ✅ {r.get('filename', 'unknown')}: Form ID {form_id}, {fields} fields, {conf:.1f}% confidence")
            if form_id != 'N/A':
                print(f"      View at: http://localhost:5173/forms/{form_id}")
    
    print(f"\n💡 Next Steps:")
    print(f"1. Review forms in the UI (http://localhost:5173)")
    print(f"2. Verify and correct extracted fields")
    print(f"3. System will learn from your corrections")
    print(f"4. Train model after 50+ verified forms")
    
    return results


if __name__ == "__main__":
    main()
