"""Test Tesseract OCR functionality"""
import asyncio
from backend.ocr import get_ocr_provider
from PIL import Image

async def test_tesseract():
    """Test Tesseract OCR with full pipeline"""
    print("Testing Tesseract OCR...")
    
    try:
        # Get provider
        provider = get_ocr_provider('tesseract')
        print(f"✓ Provider created: {type(provider).__name__}")
        print(f"✓ Is available: {provider.is_available()}")
        
        # Load test image
        img = Image.open('test_form.png')
        print(f"✓ Image loaded: {img.size}, mode: {img.mode}")
        
        # Extract text
        result = await provider.extract_text(img, preprocess=True)
        
        print("\n=== OCR Results ===")
        print(f"Status: SUCCESS")
        print(f"Text length: {len(result.get('raw_text', ''))} characters")
        print(f"Confidence: {result.get('confidence', 0)}%")
        print(f"Word count: {result.get('word_count', 0)}")
        print(f"PSM mode: {result.get('psm_mode', 'N/A')}")
        print(f"\nExtracted text preview:")
        print(result.get('raw_text', '')[:300])
        print("\n✓ Tesseract OCR is working correctly!")
        return True
        
    except Exception as e:
        print(f"\n✗ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_tesseract())
    exit(0 if success else 1)


