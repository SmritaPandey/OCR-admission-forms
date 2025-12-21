"""
Test Empty Form Detection
Test the system's ability to detect empty form templates vs filled forms
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.utils.empty_form_detector import EmptyFormDetector
from backend.ocr import get_ocr_provider
from backend.utils.file_handler import load_all_pdf_pages


async def test_empty_form_detection(pdf_path: str):
    """Test empty form detection on a PDF"""
    print(f"\n{'='*60}")
    print(f"Testing Empty Form Detection: {Path(pdf_path).name}")
    print(f"{'='*60}")
    
    try:
        # Load PDF
        pages = load_all_pdf_pages(pdf_path)
        if not pages:
            print(f"❌ Failed to load PDF")
            return
        
        image = pages[0]  # Test first page
        
        # Try to get OCR provider (may not be available)
        try:
            provider = get_ocr_provider('tesseract')  # Use tesseract as fallback
            ocr_result = await provider.extract_text(image)
        except Exception as e:
            print(f"⚠️  OCR not available: {e}")
            print("   Creating mock OCR result for testing...")
            # Mock OCR result for testing
            ocr_result = {
                'raw_text': 'STUDENT ADMISSION FORM\nName: _______________\nDate of Birth: ___________\nPhone: _______________\nEmail: _______________',
                'confidence': 85.0,
                'provider': 'mock'
            }
        
        # Detect if empty
        detector = EmptyFormDetector()
        detection = detector.detect_empty(ocr_result)
        
        # Display results
        print(f"\n📄 OCR Text Preview:")
        text = ocr_result.get('raw_text', '')
        preview = text[:300] + "..." if len(text) > 300 else text
        print(f"   {preview}")
        
        print(f"\n🔍 Empty Form Detection:")
        print(f"   Is Empty: {detection.get('is_empty')}")
        print(f"   Confidence: {detection.get('confidence', 0)*100:.1f}%")
        print(f"   Reason: {detection.get('reason')}")
        
        if detection.get('suggestions'):
            print(f"\n💡 Suggestions:")
            for suggestion in detection['suggestions']:
                print(f"   • {suggestion}")
        
        if detection.get('is_empty'):
            print(f"\n⚠️  {detector.get_empty_form_message()}")
        
        return detection
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


async def main():
    """Main test function"""
    print("="*60)
    print("Empty Form Detection Test")
    print("="*60)
    print("\nNote: These PDFs are empty form templates.")
    print("The system should detect them as empty and provide guidance.")
    print()
    
    # Find PDFs
    pdf_dir = Path("data/samples/pdfs")
    if not pdf_dir.exists():
        print(f"❌ PDF directory not found: {pdf_dir}")
        return
    
    pdfs = list(pdf_dir.glob("*.pdf"))
    if not pdfs:
        print(f"❌ No PDFs found in {pdf_dir}")
        return
    
    print(f"📁 Found {len(pdfs)} PDF files (empty form templates)")
    print(f"\n🎯 Testing with first few PDFs...\n")
    
    # Test with first 3 PDFs
    for pdf in pdfs[:3]:
        await test_empty_form_detection(str(pdf))
        print()
    
    print("="*60)
    print("Test Complete!")
    print("="*60)
    print("\n💡 Next Steps:")
    print("1. Students should fill out these forms")
    print("2. Scan the filled forms clearly")
    print("3. Upload filled forms for processing")
    print("4. System will extract student data from filled forms")


if __name__ == "__main__":
    asyncio.run(main())
