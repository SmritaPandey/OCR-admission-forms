"""
Test Script for CRAFT + TR-OCR

Demonstrates how to use CRAFT + TR-OCR for handwritten text extraction.
Perfect for testing your trained models!
"""
import asyncio
import argparse
from pathlib import Path
from PIL import Image
import sys

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.ocr.craft_trocr_provider import CraftTrocrProvider


async def test_single_image(image_path: str, custom_model: str = None):
    """Test CRAFT + TR-OCR on a single image"""
    print("=" * 80)
    print("CRAFT + TR-OCR Test")
    print("=" * 80)
    print(f"Image: {image_path}")
    if custom_model:
        print(f"Custom Model: {custom_model}")
    print()
    
    # Initialize provider
    provider = CraftTrocrProvider(custom_model_path=custom_model)
    
    # Check availability
    if not provider.is_available():
        print("❌ CRAFT + TR-OCR is not available")
        print("   Please install dependencies:")
        print("   pip install craft-text-detector transformers torch")
        return
    
    print("✅ Provider initialized")
    print()
    
    # Load image
    try:
        image = Image.open(image_path).convert("RGB")
        print(f"✅ Image loaded: {image.size[0]}x{image.size[1]} pixels")
    except Exception as e:
        print(f"❌ Error loading image: {e}")
        return
    
    print()
    print("Processing image...")
    print("-" * 80)
    
    # Extract text
    try:
        result = await provider.extract_text(image)
        
        print()
        print("=" * 80)
        print("Results")
        print("=" * 80)
        print()
        print(f"Extracted Text:")
        print("-" * 80)
        print(result['raw_text'])
        print("-" * 80)
        print()
        print(f"Confidence: {result['confidence']:.2f}%")
        print(f"Regions Detected: {result['regions_detected']}")
        print(f"Regions Recognized: {result['regions_recognized']}")
        print(f"Device: {result.get('device', 'unknown')}")
        print()
        
        # Show region details
        if result.get('regions'):
            print("Region Details:")
            print("-" * 80)
            for i, region in enumerate(result['regions'], 1):
                print(f"\nRegion {i}:")
                print(f"  Text: {region['text']}")
                print(f"  BBox: {region['bbox']}")
                print(f"  Confidence: {region['confidence']:.2f}%")
        
    except Exception as e:
        print(f"❌ Error during extraction: {e}")
        import traceback
        traceback.print_exc()


async def test_batch(images_dir: str, custom_model: str = None):
    """Test CRAFT + TR-OCR on multiple images"""
    images_dir = Path(images_dir)
    image_files = list(images_dir.glob("*.jpg")) + \
                  list(images_dir.glob("*.jpeg")) + \
                  list(images_dir.glob("*.png"))
    
    if not image_files:
        print(f"❌ No images found in {images_dir}")
        return
    
    print(f"Found {len(image_files)} images")
    print()
    
    provider = CraftTrocrProvider(custom_model_path=custom_model)
    
    if not provider.is_available():
        print("❌ CRAFT + TR-OCR is not available")
        return
    
    results = []
    for image_file in image_files:
        print(f"Processing: {image_file.name}...")
        try:
            image = Image.open(image_file).convert("RGB")
            result = await provider.extract_text(image)
            results.append({
                "file": image_file.name,
                "text": result['raw_text'],
                "confidence": result['confidence'],
                "regions": result['regions_detected']
            })
            print(f"  ✅ Extracted {len(result['raw_text'])} characters")
        except Exception as e:
            print(f"  ❌ Error: {e}")
            results.append({
                "file": image_file.name,
                "error": str(e)
            })
    
    # Summary
    print()
    print("=" * 80)
    print("Batch Processing Summary")
    print("=" * 80)
    print()
    for result in results:
        if 'error' in result:
            print(f"❌ {result['file']}: {result['error']}")
        else:
            print(f"✅ {result['file']}: {result['confidence']:.1f}% confidence, "
                  f"{result['regions']} regions, {len(result['text'])} chars")


def main():
    parser = argparse.ArgumentParser(
        description="Test CRAFT + TR-OCR on images",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("image", help="Image file or directory to test")
    parser.add_argument("--model", help="Path to custom trained model")
    parser.add_argument("--batch", action="store_true", help="Process directory of images")
    
    args = parser.parse_args()
    
    if args.batch or Path(args.image).is_dir():
        asyncio.run(test_batch(args.image, args.model))
    else:
        asyncio.run(test_single_image(args.image, args.model))


if __name__ == "__main__":
    main()

