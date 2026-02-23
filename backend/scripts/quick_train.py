#!/usr/bin/env python3
"""
Quick Training Script
Automates the entire training workflow for admission forms OCR
"""
import requests
import json
import sys
from pathlib import Path
from typing import List, Dict, Any
import time

API_BASE_URL = "http://localhost:8000/api"


def print_step(step: str, message: str):
    """Print formatted step message"""
    print(f"\n{'='*60}")
    print(f"STEP {step}: {message}")
    print('='*60)


def get_unannotated_forms(limit: int = 100) -> List[int]:
    """Get list of unannotated form IDs"""
    print_step("1", "Finding unannotated forms...")
    
    try:
        response = requests.get(f"{API_BASE_URL}/training/forms/unannotated?limit={limit}")
        response.raise_for_status()
        data = response.json()
        
        form_ids = [form['id'] for form in data.get('forms', [])]
        print(f"✅ Found {len(form_ids)} unannotated forms")
        return form_ids
    except Exception as e:
        print(f"❌ Error: {e}")
        return []


def auto_label_forms(form_ids: List[int], save: bool = True) -> Dict[str, Any]:
    """Auto-label multiple forms"""
    print_step("2", f"Auto-labeling {len(form_ids)} forms...")
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/auto-label/bulk",
            json={"form_ids": form_ids},
            params={"save_annotations": save}
        )
        response.raise_for_status()
        data = response.json()
        
        print(f"✅ Processed {data.get('processed', 0)} forms")
        print(f"   Fields extracted: {data.get('total_fields_extracted', 0)}")
        print(f"   Checkboxes extracted: {data.get('total_checkboxes_extracted', 0)}")
        return data
    except Exception as e:
        print(f"❌ Error: {e}")
        return {}


def get_training_stats() -> Dict[str, Any]:
    """Get training statistics"""
    try:
        response = requests.get(f"{API_BASE_URL}/training/stats")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Error getting stats: {e}")
        return {}


def prepare_training_data(format: str = "both", split: bool = True) -> Dict[str, Any]:
    """Prepare training data"""
    print_step("3", "Preparing training data...")
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/training/prepare-data",
            params={"format": format, "split": split}
        )
        response.raise_for_status()
        data = response.json()
        
        print(f"✅ Extracted {data.get('samples_extracted', 0)} training samples")
        if 'datasets' in data:
            for dataset_type, dataset_info in data['datasets'].items():
                if 'error' not in dataset_info:
                    print(f"   {dataset_type.upper()}: {dataset_info.get('samples', 0)} samples")
                    if 'splits' in dataset_info:
                        print(f"     Train/Val/Test splits created")
        
        return data
    except Exception as e:
        print(f"❌ Error: {e}")
        return {}


def print_training_instructions():
    """Print instructions for manual training"""
    print_step("4", "Training Instructions")
    
    print("""
To train your model, run one of these commands:

For TrOCR (handwriting):
  cd backend/training
  python train_trocr.py \\
    ../uploads/training_data/train.json \\
    ../models/trocr_finetuned \\
    --val-data ../uploads/training_data/val.json \\
    --epochs 10 \\
    --batch-size 8 \\
    --learning-rate 5e-5 \\
    --base-model microsoft/trocr-base-handwritten

For Donut (structured forms):
  cd backend/training
  python train_donut.py \\
    ../uploads/training_data/train.json \\
    ../models/donut_finetuned \\
    --val-data ../uploads/training_data/val.json \\
    --epochs 15 \\
    --batch-size 4 \\
    --learning-rate 3e-5

Or use the training API:
  curl -X POST "http://localhost:8000/api/training/start" \\
    -H "Content-Type: application/json" \\
    -d '{
      "model_type": "trocr",
      "epochs": 10,
      "batch_size": 8,
      "learning_rate": 5e-5
    }'
""")


def main():
    """Main training workflow"""
    print("\n" + "="*60)
    print("QUICK TRAINING WORKFLOW FOR ADMISSION FORMS OCR")
    print("="*60)
    
    # Step 1: Get unannotated forms
    form_ids = get_unannotated_forms(limit=100)
    
    if not form_ids:
        print("\n⚠️  No unannotated forms found. Checking if any forms are uploaded...")
        stats = get_training_stats()
        if stats:
            print(f"   Total forms: {stats.get('total_forms', 0)}")
            print(f"   Annotated: {stats.get('annotated_forms', 0)}")
        
        proceed = input("\nProceed with preparing training data for existing annotations? (y/n): ")
        if proceed.lower() != 'y':
            print("Exiting...")
            return
    else:
        # Step 2: Auto-label forms
        auto_label_forms(form_ids, save=True)
        
        # Show updated stats
        stats = get_training_stats()
        if stats:
            print(f"\n📊 Current Statistics:")
            print(f"   Annotated forms: {stats.get('annotated_forms', 0)}")
            print(f"   Total fields: {stats.get('total_fields', 0)}")
            print(f"   Total checkboxes: {stats.get('total_checkboxes', 0)}")
    
    # Step 3: Prepare training data
    prepare_training_data(format="both", split=True)
    
    # Step 4: Print training instructions
    print_training_instructions()
    
    print("\n" + "="*60)
    print("✅ QUICK TRAINING WORKFLOW COMPLETE!")
    print("="*60)
    print("\nNext steps:")
    print("1. Review auto-labeled forms and correct if needed")
    print("2. Add more forms if needed (aim for 100-200 annotated forms)")
    print("3. Run training commands above")
    print("4. Evaluate trained model on test set")
    print("\nFor detailed guide, see: COMPLETE_TRAINING_GUIDE.md")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
