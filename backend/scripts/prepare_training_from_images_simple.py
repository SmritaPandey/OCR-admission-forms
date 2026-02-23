"""
Simple script to prepare training data from converted images
Uses CRAFT+TR-OCR to extract text from images for training
"""
import json
import sys
from pathlib import Path
from PIL import Image
import asyncio

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.ocr import get_ocr_provider

async def prepare_training_data():
    """Prepare training data from images using CRAFT+TR-OCR"""
    project_root = Path(__file__).parent.parent.parent
    images_dir = project_root / "data" / "samples" / "images"
    output_file = project_root / "training_data" / "student_forms.json"
    
    if not images_dir.exists():
        print(f"Error: Images directory not found: {images_dir}")
        return
    
    # Get all image files
    image_files = sorted(list(images_dir.glob("*.png")))
    
    if not image_files:
        print(f"No image files found in {images_dir}")
        return
    
    print(f"Found {len(image_files)} image files")
    print("Processing with CRAFT+TR-OCR...")
    print()
    
    training_data = []
    
    # Use Tesseract (most reliable for initial training data)
    # We'll train CRAFT+TR-OCR on this data
    try:
        provider = get_ocr_provider("tesseract")
        print("✅ Tesseract provider loaded")
        print("   (Using Tesseract to extract text, will train CRAFT+TR-OCR on this data)")
    except Exception as e:
        print(f"❌ Tesseract not available: {e}")
        return
    
    processed = 0
    for img_file in image_files:
        try:
            print(f"Processing {processed + 1}/{len(image_files)}: {img_file.name[:50]}...", end=" ", flush=True)
            
            # Load image
            image = Image.open(img_file)
            
            # Extract text
            result = await provider.extract_text(image)
            
            if result.get('raw_text'):
                training_data.append({
                    'image_path': str(img_file.relative_to(project_root)),
                    'text': result['raw_text'],
                    'confidence': result.get('confidence', 0.0)
                })
                print(f"✅ ({len(result['raw_text'])} chars)")
                processed += 1
            else:
                print("⚠️  No text extracted")
            
        except Exception as e:
            print(f"❌ Error: {str(e)[:50]}")
            continue
    
    # Save training data
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(training_data, f, indent=2, ensure_ascii=False)
    
    print()
    print(f"✅ Training data prepared!")
    print(f"   Total samples: {len(training_data)}")
    print(f"   Output file: {output_file}")

if __name__ == "__main__":
    asyncio.run(prepare_training_data())
