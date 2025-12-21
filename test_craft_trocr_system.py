"""
Test CRAFT-TROCR System with Sample PDFs
Tests the complete system with PDFs from data/samples/pdfs/
"""
import asyncio
import sys
from pathlib import Path
from PIL import Image
import requests
import json

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.ocr.ocr_factory import OCRFactory
from backend.utils.file_handler import load_all_pdf_pages
from backend.config import settings


async def test_ocr_provider(provider_name: str, image_path: str):
    """Test a specific OCR provider"""
    print(f"\n{'='*60}")
    print(f"Testing {provider_name} on {Path(image_path).name}")
    print(f"{'='*60}")
    
    try:
        # Check if provider is available
        available = OCRFactory.get_available_providers()
        if provider_name not in available:
            print(f"⚠️  Provider {provider_name} not available. Available: {available}")
            return None
        
        # Create provider
        provider = OCRFactory.create_provider(provider_name)
        
        # Load image
        if image_path.endswith('.pdf'):
            pages = load_all_pdf_pages(image_path)
            if not pages:
                print(f"❌ Failed to load PDF: {image_path}")
                return None
            image = pages[0]  # Test first page
        else:
            from backend.utils.file_handler import load_image
            image = load_image(image_path)
        
        # Extract text
        print(f"Extracting text...")
        result = await provider.extract_text(image)
        
        # Display results
        print(f"\n✅ Extraction successful!")
        print(f"   Provider: {result.get('provider', provider_name)}")
        print(f"   Confidence: {result.get('confidence', 0):.1f}%")
        print(f"   Text length: {len(result.get('raw_text', ''))} chars")
        print(f"   Word count: {result.get('structured_data', {}).get('word_count', 'N/A')}")
        
        # Show preview of text
        text = result.get('raw_text', '')
        if text:
            preview = text[:200] + "..." if len(text) > 200 else text
            print(f"\n   Text preview:\n   {preview}")
        
        return result
    
    except Exception as e:
        print(f"❌ Error testing {provider_name}: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_all_providers(pdf_path: str):
    """Test all available providers on a PDF"""
    print(f"\n{'#'*60}")
    print(f"Testing all providers on: {Path(pdf_path).name}")
    print(f"{'#'*60}")
    
    providers_to_test = [
        'craft-trocr',
        'craft',
        'trocr',
        'tesseract',
    ]
    
    results = {}
    for provider in providers_to_test:
        result = await test_ocr_provider(provider, pdf_path)
        if result:
            results[provider] = result
    
    return results


async def test_api_upload(pdf_path: str, base_url: str = "http://localhost:8000"):
    """Test API upload endpoint"""
    print(f"\n{'#'*60}")
    print(f"Testing API upload: {Path(pdf_path).name}")
    print(f"{'#'*60}")
    
    try:
        with open(pdf_path, 'rb') as f:
            files = {'file': (Path(pdf_path).name, f, 'application/pdf')}
            data = {'ocr_provider': 'craft-trocr'}
            
            response = requests.post(
                f"{base_url}/api/upload",
                files=files,
                data=data,
                timeout=120
            )
            
            if response.status_code == 201:
                form_data = response.json()
                print(f"✅ Upload successful!")
                print(f"   Form ID: {form_data.get('id')}")
                print(f"   Status: {form_data.get('status')}")
                print(f"   Provider: {form_data.get('ocr_provider')}")
                return form_data
            else:
                print(f"❌ Upload failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return None
    
    except requests.exceptions.ConnectionError:
        print(f"⚠️  API server not running at {base_url}")
        print(f"   Start server with: python -m uvicorn backend.main:app --reload")
        return None
    except Exception as e:
        print(f"❌ Error testing API: {e}")
        import traceback
        traceback.print_exc()
        return None


async def main():
    """Main test function"""
    print("="*60)
    print("CRAFT-TROCR System Test Suite")
    print("="*60)
    
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
    
    # Test with first PDF (or specific one)
    test_pdf = pdfs[0]  # Test with first PDF
    print(f"\n🎯 Testing with: {test_pdf.name}")
    
    # Test 1: Direct OCR provider test
    print("\n" + "="*60)
    print("TEST 1: Direct OCR Provider Test")
    print("="*60)
    
    # Test CRAFT-TROCR if available
    craft_trocr_available = 'craft-trocr' in OCRFactory.get_available_providers()
    if craft_trocr_available:
        result = await test_ocr_provider('craft-trocr', str(test_pdf))
        if result:
            print("\n✅ CRAFT-TROCR test passed!")
        else:
            print("\n⚠️  CRAFT-TROCR test failed or not available")
    else:
        print("\n⚠️  CRAFT-TROCR not available. Install dependencies:")
        print("   pip install craft-text-detector transformers torch torchvision")
    
    # Test 2: API upload test
    print("\n" + "="*60)
    print("TEST 2: API Upload Test")
    print("="*60)
    
    form_data = await test_api_upload(str(test_pdf))
    if form_data:
        form_id = form_data.get('id')
        if form_id:
            print(f"\n✅ API test passed! Form ID: {form_id}")
            print(f"   View form at: http://localhost:5173/forms/{form_id}")
    
    # Test 3: Test all providers on one PDF
    print("\n" + "="*60)
    print("TEST 3: All Providers Comparison")
    print("="*60)
    
    results = await test_all_providers(str(test_pdf))
    
    if results:
        print(f"\n📊 Results Summary:")
        print(f"{'Provider':<20} {'Confidence':<15} {'Text Length':<15}")
        print("-" * 50)
        for provider, result in results.items():
            conf = result.get('confidence', 0)
            text_len = len(result.get('raw_text', ''))
            print(f"{provider:<20} {conf:<15.1f} {text_len:<15}")
    
    print("\n" + "="*60)
    print("Test Suite Complete!")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
