#!/usr/bin/env python3
"""
Test all OCR providers including Ollama with llama3.2-vision
"""
import sys
import asyncio
from pathlib import Path
from PIL import Image
import json

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.ocr import get_ocr_provider, OCRFactory
from backend.config import settings

async def test_provider(provider_name: str, image_path: str):
    """Test a single OCR provider"""
    print(f"\n{'='*60}")
    print(f"Testing: {provider_name}")
    print(f"{'='*60}")
    
    try:
        # Check if provider is available
        providers = OCRFactory.get_available_providers()
        if provider_name not in providers:
            print(f"❌ Provider '{provider_name}' not available")
            return None
        
        # Get provider
        provider = get_ocr_provider(provider_name)
        
        # Check availability
        if not provider.is_available():
            print(f"⚠️  Provider '{provider_name}' is not available (dependencies missing)")
            return None
        
        print(f"✅ Provider loaded successfully")
        
        # Load image
        image = Image.open(image_path)
        print(f"📄 Image: {image_path}")
        print(f"   Size: {image.size[0]}x{image.size[1]}")
        
        # Extract text
        print(f"⏳ Processing...")
        result = await provider.extract_text(image)
        
        # Display results
        print(f"\n📊 Results:")
        print(f"   Provider: {result.get('provider', provider_name)}")
        print(f"   Confidence: {result.get('confidence', 0):.2f}%")
        
        raw_text = result.get('raw_text', '')
        if raw_text:
            text_preview = raw_text[:200].replace('\n', ' ')
            print(f"   Text preview: {text_preview}...")
            print(f"   Total characters: {len(raw_text)}")
        else:
            print(f"   ⚠️  No text extracted")
        
        # Show structured data if available
        structured_data = result.get('structured_data')
        if structured_data:
            print(f"   ✅ Structured data available")
            print(f"   Fields extracted: {len([k for k, v in structured_data.items() if v])}")
        
        # Show metadata if available
        metadata = result.get('metadata', {})
        if metadata:
            print(f"   Metadata: {json.dumps(metadata, indent=6)}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

async def test_all_providers(image_path: str):
    """Test all available OCR providers"""
    print(f"\n{'='*60}")
    print(f"OCR Provider Test Suite")
    print(f"{'='*60}")
    print(f"\nImage: {image_path}")
    
    # Get all available providers
    providers = OCRFactory.get_available_providers()
    print(f"\n📋 Available providers: {', '.join(sorted(providers))}")
    
    # Test providers in order of preference
    test_order = [
        'ollama',           # Test Ollama first (user requested)
        'craft-trocr',      # Best for handwritten
        'craft',
        'trocr',
        'tesseract',        # Free fallback
        'google-vision',
        'google-documentai',
        'azure-vision',
        'azure-form-recognizer',
        'aws-textract',
        'gpt4-vision',
        'claude-vision',
    ]
    
    results = {}
    
    for provider_name in test_order:
        if provider_name in providers:
            result = await test_provider(provider_name, image_path)
            if result:
                results[provider_name] = result
            # Small delay between tests
            await asyncio.sleep(1)
    
    # Test any remaining providers
    for provider_name in sorted(providers):
        if provider_name not in results and provider_name not in test_order:
            result = await test_provider(provider_name, image_path)
            if result:
                results[provider_name] = result
            await asyncio.sleep(1)
    
    # Summary
    print(f"\n{'='*60}")
    print(f"Test Summary")
    print(f"{'='*60}")
    print(f"Total providers tested: {len(results)}")
    
    if results:
        print(f"\n📊 Results by Provider:")
        for provider_name, result in results.items():
            confidence = result.get('confidence', 0)
            text_len = len(result.get('raw_text', ''))
            print(f"   {provider_name:20s} | Confidence: {confidence:6.2f}% | Text: {text_len:5d} chars")
        
        # Best provider
        best = max(results.items(), key=lambda x: x[1].get('confidence', 0))
        print(f"\n🏆 Best Provider: {best[0]} (Confidence: {best[1].get('confidence', 0):.2f}%)")
    
    return results

async def test_ollama_specific(image_path: str):
    """Test Ollama specifically with llama3.2-vision"""
    print(f"\n{'='*60}")
    print(f"Ollama Specific Test (llama3.2-vision)")
    print(f"{'='*60}")
    
    try:
        provider = get_ocr_provider('ollama')
        
        if not provider.is_available():
            print("❌ Ollama is not available")
            print("   Make sure Ollama is running: ollama serve")
            print("   Pull the model: ollama pull llama3.2-vision")
            return None
        
        print("✅ Ollama provider loaded")
        print(f"   Model: {provider.model}")
        print(f"   Base URL: {provider.base_url}")
        
        # Load image
        image = Image.open(image_path)
        print(f"\n📄 Processing image: {image_path}")
        
        # Extract text
        print("⏳ Extracting text (this may take 30-60 seconds)...")
        result = await provider.extract_text(image)
        
        # Display results
        print(f"\n📊 Results:")
        print(f"   Confidence: {result.get('confidence', 0):.2f}%")
        
        raw_text = result.get('raw_text', '')
        if raw_text:
            print(f"   Text length: {len(raw_text)} characters")
            print(f"\n📝 Extracted Text:")
            print(f"{'-'*60}")
            print(raw_text[:500])
            if len(raw_text) > 500:
                print(f"... ({len(raw_text) - 500} more characters)")
            print(f"{'-'*60}")
        
        structured_data = result.get('structured_data', {})
        if structured_data:
            print(f"\n📋 Structured Data:")
            print(json.dumps(structured_data, indent=2))
        
        metadata = result.get('metadata', {})
        if metadata:
            print(f"\n🔧 Metadata:")
            print(json.dumps(metadata, indent=2))
        
        return result
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Main test function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test OCR providers")
    parser.add_argument('image', help='Path to test image')
    parser.add_argument('--provider', help='Test specific provider only')
    parser.add_argument('--ollama-only', action='store_true', help='Test only Ollama')
    parser.add_argument('--all', action='store_true', help='Test all providers')
    
    args = parser.parse_args()
    
    image_path = Path(args.image)
    if not image_path.exists():
        print(f"❌ Error: Image not found: {image_path}")
        return
    
    if args.ollama_only:
        asyncio.run(test_ollama_specific(str(image_path)))
    elif args.provider:
        asyncio.run(test_provider(args.provider, str(image_path)))
    else:
        asyncio.run(test_all_providers(str(image_path)))

if __name__ == "__main__":
    main()
