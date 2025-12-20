"""
Data Preparation Script for CRAFT + TR-OCR Training

Converts various data formats into the JSON format required for training.
Supports:
- CSV files
- Directory of images with text files
- Existing OCR results
- Manual annotations
"""
import argparse
import json
import csv
from pathlib import Path
from typing import List, Dict, Any
from PIL import Image
import sys


def prepare_from_csv(csv_path: str, image_dir: str, output_path: str):
    """Convert CSV file to training format"""
    data = []
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            image_path = row.get('image_path', row.get('image', ''))
            text = row.get('text', row.get('label', row.get('ground_truth', '')))
            
            if not image_path or not text:
                continue
            
            # Resolve image path
            if not Path(image_path).is_absolute():
                image_path = str(Path(image_dir) / image_path)
            
            if Path(image_path).exists():
                data.append({
                    "image_path": image_path,
                    "text": text.strip()
                })
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Converted {len(data)} samples from CSV to {output_path}")
    return data


def prepare_from_directory(image_dir: str, text_dir: str, output_path: str):
    """Convert directory of images with corresponding text files"""
    data = []
    image_dir = Path(image_dir)
    text_dir = Path(text_dir) if text_dir else image_dir
    
    # Find all images
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff'}
    images = [f for f in image_dir.iterdir() if f.suffix.lower() in image_extensions]
    
    for image_path in images:
        # Look for corresponding text file
        text_file = text_dir / f"{image_path.stem}.txt"
        
        if text_file.exists():
            text = text_file.read_text(encoding='utf-8').strip()
            if text:
                data.append({
                    "image_path": str(image_path),
                    "text": text
                })
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Converted {len(data)} samples from directory to {output_path}")
    return data


def prepare_from_ocr_results(results_dir: str, output_path: str):
    """Convert existing OCR results to training format"""
    data = []
    results_dir = Path(results_dir)
    
    # Look for JSON files with OCR results
    for json_file in results_dir.glob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                result = json.load(f)
            
            image_path = result.get('image_path') or result.get('file_path')
            text = result.get('text') or result.get('raw_text') or result.get('extracted_text')
            
            if image_path and text and Path(image_path).exists():
                data.append({
                    "image_path": str(Path(image_path).absolute()),
                    "text": text.strip()
                })
        except Exception as e:
            print(f"⚠️  Error processing {json_file}: {e}")
            continue
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Converted {len(data)} samples from OCR results to {output_path}")
    return data


def validate_data(data_path: str, image_dir: str = None):
    """Validate training data"""
    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    valid = []
    invalid = []
    
    for i, item in enumerate(data):
        image_path = item.get('image_path', '')
        text = item.get('text', '')
        
        # Resolve path
        if image_dir and not Path(image_path).is_absolute():
            image_path = str(Path(image_dir) / image_path)
        
        if not Path(image_path).exists():
            invalid.append(f"Sample {i}: Image not found: {image_path}")
            continue
        
        if not text or not text.strip():
            invalid.append(f"Sample {i}: Empty text")
            continue
        
        # Verify image can be opened
        try:
            img = Image.open(image_path)
            img.verify()
        except Exception as e:
            invalid.append(f"Sample {i}: Invalid image: {e}")
            continue
        
        valid.append(item)
    
    print(f"\nValidation Results:")
    print(f"  Valid samples: {len(valid)}")
    print(f"  Invalid samples: {len(invalid)}")
    
    if invalid:
        print(f"\n⚠️  Invalid samples:")
        for error in invalid[:10]:  # Show first 10
            print(f"    {error}")
        if len(invalid) > 10:
            print(f"    ... and {len(invalid) - 10} more")
    
    return valid, invalid


def main():
    parser = argparse.ArgumentParser(
        description="Prepare training data for CRAFT + TR-OCR",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Data source type')
    
    # CSV parser
    csv_parser = subparsers.add_parser('csv', help='Convert from CSV')
    csv_parser.add_argument('csv_file', help='Input CSV file')
    csv_parser.add_argument('image_dir', help='Directory containing images')
    csv_parser.add_argument('output', help='Output JSON file')
    
    # Directory parser
    dir_parser = subparsers.add_parser('directory', help='Convert from directory')
    dir_parser.add_argument('image_dir', help='Directory containing images')
    dir_parser.add_argument('output', help='Output JSON file')
    dir_parser.add_argument('--text-dir', help='Directory containing text files (default: same as image_dir)')
    
    # OCR results parser
    ocr_parser = subparsers.add_parser('ocr', help='Convert from OCR results')
    ocr_parser.add_argument('results_dir', help='Directory containing OCR result JSON files')
    ocr_parser.add_argument('output', help='Output JSON file')
    
    # Validate parser
    validate_parser = subparsers.add_parser('validate', help='Validate training data')
    validate_parser.add_argument('data_file', help='Training data JSON file')
    validate_parser.add_argument('--image-dir', help='Image directory (if paths are relative)')
    
    args = parser.parse_args()
    
    if args.command == 'csv':
        prepare_from_csv(args.csv_file, args.image_dir, args.output)
    elif args.command == 'directory':
        prepare_from_directory(args.image_dir, args.text_dir, args.output)
    elif args.command == 'ocr':
        prepare_from_ocr_results(args.results_dir, args.output)
    elif args.command == 'validate':
        validate_data(args.data_file, args.image_dir)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

