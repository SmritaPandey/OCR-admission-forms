#!/usr/bin/env python3
"""
Prepare training data from verified forms with annotations
Converts verified form annotations to CRAFT+TR-OCR training format
"""
import sys
import json
import asyncio
from pathlib import Path
from PIL import Image
from typing import List, Dict, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.database import SessionLocal, AdmissionForm
from backend.utils.file_handler import load_image
from backend.config import settings

def get_annotated_forms():
    """Get all verified forms with annotations"""
    db = SessionLocal()
    try:
        forms = db.query(AdmissionForm).filter(
            AdmissionForm.status == 'verified',
            AdmissionForm.additional_info.isnot(None)
        ).all()
        
        annotated_forms = []
        for form in forms:
            if form.additional_info and 'annotation' in form.additional_info:
                annotation = form.additional_info['annotation']
                if annotation.get('key_value_pairs'):
                    annotated_forms.append({
                        'form_id': form.id,
                        'file_path': form.file_path,
                        'filename': form.filename,
                        'annotation': annotation
                    })
        
        return annotated_forms
    finally:
        db.close()

def prepare_trocr_training_data(annotated_forms: List[Dict[str, Any]], output_file: Path):
    """Prepare TR-OCR training data from annotations"""
    training_data = []
    
    print(f"\n📝 Preparing training data from {len(annotated_forms)} annotated forms...")
    
    for i, form_data in enumerate(annotated_forms, 1):
        try:
            file_path = Path(settings.UPLOAD_DIR) / form_data['file_path']
            
            if not file_path.exists():
                print(f"⚠️  Form {i}/{len(annotated_forms)}: File not found: {file_path}")
                continue
            
            # Load image
            try:
                image = load_image(str(file_path))
            except Exception as e:
                print(f"⚠️  Form {i}/{len(annotated_forms)}: Failed to load image: {e}")
                continue
            
            # Get annotation
            annotation = form_data['annotation']
            key_value_pairs = annotation.get('key_value_pairs', {})
            
            # Create text from key-value pairs (ground truth)
            text_lines = []
            for key, value in key_value_pairs.items():
                if value and str(value).strip():
                    text_lines.append(f"{key}: {value}")
            
            ground_truth_text = "\n".join(text_lines)
            
            if not ground_truth_text.strip():
                print(f"⚠️  Form {i}/{len(annotated_forms)}: No text in annotation")
                continue
            
            # Add to training data
            training_data.append({
                'image_path': str(file_path.relative_to(Path('.'))),
                'text': ground_truth_text,
                'form_id': form_data['form_id'],
                'fields_count': len(key_value_pairs)
            })
            
            print(f"✅ Form {i}/{len(annotated_forms)}: {form_data['filename']} ({len(key_value_pairs)} fields)")
            
        except Exception as e:
            print(f"❌ Form {i}/{len(annotated_forms)}: Error: {e}")
            continue
    
    # Save training data
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(training_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Training data prepared!")
    print(f"   Total samples: {len(training_data)}")
    print(f"   Output file: {output_file}")
    
    return training_data

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Prepare training data from annotated forms")
    parser.add_argument('--output', default='training_data/annotated_forms_training.json',
                       help='Output file path')
    parser.add_argument('--min-forms', type=int, default=10,
                       help='Minimum number of forms required')
    
    args = parser.parse_args()
    
    print("="*60)
    print("Training Data Preparation from Annotations")
    print("="*60)
    
    # Get annotated forms
    print("\n📋 Fetching annotated forms from database...")
    annotated_forms = get_annotated_forms()
    
    if not annotated_forms:
        print("\n❌ No annotated forms found!")
        print("   Please verify some forms first - annotations are created automatically when you verify.")
        return
    
    print(f"✅ Found {len(annotated_forms)} annotated forms")
    
    if len(annotated_forms) < args.min_forms:
        print(f"\n⚠️  Warning: Only {len(annotated_forms)} forms found (minimum recommended: {args.min_forms})")
        print("   Training may not be effective with this few samples.")
        response = input("   Continue anyway? (y/n): ")
        if response.lower() != 'y':
            return
    
    # Prepare training data
    output_file = Path(args.output)
    training_data = prepare_trocr_training_data(annotated_forms, output_file)
    
    if training_data:
        print(f"\n🎉 Success! Training data ready for CRAFT+TR-OCR training")
        print(f"\nNext steps:")
        print(f"  1. Review training data: cat {output_file}")
        print(f"  2. Train model: python3 backend/training/train_craft_trocr.py {output_file} models/trocr_trained --epochs 20")
        print(f"  3. Or use browser: http://localhost:5173/training")

if __name__ == "__main__":
    main()
