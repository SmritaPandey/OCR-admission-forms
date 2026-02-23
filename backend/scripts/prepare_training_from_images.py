"""
Prepare training data from converted images in data/samples/images/
This extracts text from images using all available OCR providers and prepares
training data for CRAFT and TR-OCR.
"""
import json
import sys
from pathlib import Path
from PIL import Image
import asyncio

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.ocr import get_ocr_provider
from backend.config import settings

async def prepare_training_data_from_images():
    """
    Process all images and prepare training data
    """
    project_root = Path(__file__).parent.parent.parent
    images_dir = project_root / "data" / "samples" / "images"
    output_file = project_root / "training_data" / "images_training_data.json"
    
    if not images_dir.exists():
        print(f"Error: Images directory not found: {images_dir}")
        return
    
    # Get all image files
    image_files = list(images_dir.glob("*.png")) + list(images_dir.glob("*.jpg"))
    
    if not image_files:
        print(f"No image files found in {images_dir}")
        return
    
    print(f"Found {len(image_files)} image files")
    print("Processing with multiple OCR providers...")
    print()
    
    training_data = []
    
    # Try different providers
    providers_to_try = ["craft-trocr", "craft", "trocr", "tesseract", "google-vision"]
    
    for img_file in image_files:
        print(f"Processing: {img_file.name}")
        
        try:
            # Load image
            image = Image.open(img_file)
            
            # Try each provider
            results = {}
            for provider_name in providers_to_try:
                try:
                    provider = get_ocr_provider(provider_name)
                    result = await provider.extract_text(image)
                    
                    if result.get('raw_text'):
                        results[provider_name] = {
                            'text': result['raw_text'],
                            'confidence': result.get('confidence', 0.0)
                        }
                        print(f"  ✓ {provider_name}: {len(result['raw_text'])} chars, conf={result.get('confidence', 0):.2f}")
                except Exception as e:
                    print(f"  ✗ {provider_name}: {str(e)}")
                    continue
            
            # Use the best result (highest confidence)
            if results:
                best_provider = max(results.items(), key=lambda x: x[1]['confidence'])
                best_text = best_provider[1]['text']
                
                training_data.append({
                    'image_path': str(img_file),
                    'text': best_text,
                    'provider_used': best_provider[0],
                    'confidence': best_provider[1]['confidence'],
                    'all_results': results
                })
                
                print(f"  ✅ Best: {best_provider[0]} ({best_provider[1]['confidence']:.2f})")
            else:
                print(f"  ⚠️  No OCR results")
            
            print()
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
            print()
            continue
    
    # Save training data
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(training_data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Training data prepared!")
    print(f"   Total samples: {len(training_data)}")
    print(f"   Output file: {output_file}")

if __name__ == "__main__":
    asyncio.run(prepare_training_data_from_images())
