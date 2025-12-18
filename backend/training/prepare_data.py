"""
Data Preparation Utility
Convert annotated forms to training data format for TrOCR/Donut
"""
import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from PIL import Image
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.config import settings
from backend.utils.file_handler import load_all_pdf_pages, load_image


class TrainingDataPreparator:
    """Prepare training data from annotated forms"""
    
    def __init__(self, upload_dir: Optional[str] = None):
        if upload_dir is None:
            upload_dir = settings.UPLOAD_DIR
        self.upload_dir = Path(upload_dir)
        self.training_dir = self.upload_dir / "training_data"
        self.training_dir.mkdir(parents=True, exist_ok=True)
    
    def load_annotations_from_json(self, json_path: str) -> List[Dict[str, Any]]:
        """Load annotations from exported JSON file"""
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        # Handle both direct list and wrapped format
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and 'data' in data:
            return data['data']
        else:
            raise ValueError(f"Unexpected JSON format in {json_path}")
    
    def extract_images_from_forms(
        self,
        annotated_forms: List[Dict[str, Any]],
        output_images_dir: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Extract images from form files and prepare for training
        
        Returns list of training samples with image paths and labels
        """
        if output_images_dir is None:
            output_images_dir = self.training_dir / "images"
        else:
            output_images_dir = Path(output_images_dir)
        
        output_images_dir.mkdir(parents=True, exist_ok=True)
        
        training_samples = []
        
        for form_data in annotated_forms:
            form_id = form_data.get('form_id')
            file_path = form_data.get('file_path')
            annotation = form_data.get('annotation', {})
            
            if not file_path:
                print(f"Warning: Form {form_id} has no file_path, skipping")
                continue
            
            # Resolve full file path
            full_path = self.upload_dir / file_path
            if not full_path.exists():
                print(f"Warning: File not found: {full_path}, skipping")
                continue
            
            # Extract text labels from annotations
            fields = annotation.get('fields', [])
            checkboxes = annotation.get('checkboxes', [])
            text_labels = []
            
            for field in fields:
                field_name = field.get('field_name', '')
                value = field.get('value', '')
                if value:
                    text_labels.append(f"{field_name}: {value}")
            
            # Add checkbox labels
            for cb in checkboxes:
                label = cb.get('label', '')
                checked = cb.get('checked', False)
                if label:
                    status = "✓" if checked else "☐"
                    text_labels.append(f"{label}: {status}")
            
            # Combine all text
            full_text = "\n".join(text_labels)
            
            # Load images from PDF or image file
            try:
                if full_path.suffix.lower() == '.pdf':
                    pages = load_all_pdf_pages(str(full_path))
                else:
                    pages = [load_image(str(full_path))]
                
                # Save each page as separate training sample
                for page_num, page_image in enumerate(pages):
                    # Generate unique filename
                    image_filename = f"form_{form_id}_page_{page_num + 1}.png"
                    image_path = output_images_dir / image_filename
                    
                    # Save image
                    page_image.save(image_path, "PNG")
                    
                    # Create training sample
                    sample = {
                        'image_path': str(image_path),
                        'text': full_text if page_num == 0 else "",  # Use full text for first page
                        'form_id': form_id,
                        'page_number': page_num + 1,
                        'fields': fields if page_num == 0 else [],  # Fields typically on first page
                        'checkboxes': checkboxes if page_num == 0 else []  # Checkboxes typically on first page
                    }
                    
                    training_samples.append(sample)
                    
            except Exception as e:
                print(f"Error processing form {form_id}: {e}")
                continue
        
        return training_samples
    
    def prepare_trocr_dataset(
        self,
        training_samples: List[Dict[str, Any]],
        output_file: Optional[str] = None
    ) -> Path:
        """
        Prepare dataset in TrOCR format
        
        TrOCR expects: list of {"image_path": "...", "text": "..."}
        """
        if output_file is None:
            output_file = self.training_dir / "trocr_dataset.json"
        else:
            output_file = Path(output_file)
        
        # Convert to TrOCR format
        trocr_data = []
        for sample in training_samples:
            trocr_data.append({
                'image_path': sample['image_path'],
                'text': sample['text']
            })
        
        # Save dataset
        with open(output_file, 'w') as f:
            json.dump(trocr_data, f, indent=2)
        
        print(f"✅ TrOCR dataset prepared: {output_file}")
        print(f"   Total samples: {len(trocr_data)}")
        
        return output_file
    
    def prepare_donut_dataset(
        self,
        training_samples: List[Dict[str, Any]],
        output_file: Optional[str] = None
    ) -> Path:
        """
        Prepare dataset in Donut format
        
        Donut expects: list of {"image_path": "...", "ground_truth": "..."}
        where ground_truth is JSON string
        """
        if output_file is None:
            output_file = self.training_dir / "donut_dataset.json"
        else:
            output_file = Path(output_file)
        
        # Convert to Donut format
        donut_data = []
        for sample in training_samples:
            # Create ground truth JSON from fields
            ground_truth = {}
            for field in sample.get('fields', []):
                field_name = field.get('field_name')
                value = field.get('value')
                if field_name and value:
                    ground_truth[field_name] = value
            
            # Add checkbox information
            checkboxes = sample.get('checkboxes', [])
            if checkboxes:
                checkbox_dict = {}
                for cb in checkboxes:
                    label = cb.get('label', '')
                    checked = cb.get('checked', False)
                    if label:
                        checkbox_dict[label] = checked
                if checkbox_dict:
                    ground_truth['checkboxes'] = checkbox_dict
            
            # Convert to JSON string
            ground_truth_json = json.dumps(ground_truth, ensure_ascii=False)
            
            donut_data.append({
                'image_path': sample['image_path'],
                'ground_truth': ground_truth_json
            })
        
        # Save dataset
        with open(output_file, 'w') as f:
            json.dump(donut_data, f, indent=2)
        
        print(f"✅ Donut dataset prepared: {output_file}")
        print(f"   Total samples: {len(donut_data)}")
        
        return output_file
    
    def split_dataset(
        self,
        dataset_path: str,
        train_ratio: float = 0.8,
        val_ratio: float = 0.1,
        test_ratio: float = 0.1
    ) -> Tuple[Path, Path, Path]:
        """
        Split dataset into train/val/test sets
        """
        with open(dataset_path, 'r') as f:
            data = json.load(f)
        
        import random
        random.shuffle(data)
        
        total = len(data)
        train_end = int(total * train_ratio)
        val_end = train_end + int(total * val_ratio)
        
        train_data = data[:train_end]
        val_data = data[train_end:val_end]
        test_data = data[val_end:]
        
        dataset_path_obj = Path(dataset_path)
        base_dir = dataset_path_obj.parent
        
        train_path = base_dir / "train.json"
        val_path = base_dir / "val.json"
        test_path = base_dir / "test.json"
        
        with open(train_path, 'w') as f:
            json.dump(train_data, f, indent=2)
        with open(val_path, 'w') as f:
            json.dump(val_data, f, indent=2)
        with open(test_path, 'w') as f:
            json.dump(test_data, f, indent=2)
        
        print(f"✅ Dataset split:")
        print(f"   Train: {len(train_data)} samples ({train_path})")
        print(f"   Val: {len(val_data)} samples ({val_path})")
        print(f"   Test: {len(test_data)} samples ({test_path})")
        
        return train_path, val_path, test_path


def main():
    """CLI interface for data preparation"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Prepare training data from annotations")
    parser.add_argument("annotations_json", help="Path to exported annotations JSON")
    parser.add_argument("--format", choices=["trocr", "donut", "both"], default="both",
                       help="Output format")
    parser.add_argument("--output-dir", help="Output directory for training data")
    parser.add_argument("--split", action="store_true", help="Split into train/val/test")
    
    args = parser.parse_args()
    
    preparator = TrainingDataPreparator()
    
    # Load annotations
    print(f"Loading annotations from {args.annotations_json}...")
    annotated_forms = preparator.load_annotations_from_json(args.annotations_json)
    print(f"✅ Loaded {len(annotated_forms)} annotated forms")
    
    # Extract images
    print("\nExtracting images from forms...")
    training_samples = preparator.extract_images_from_forms(annotated_forms)
    print(f"✅ Extracted {len(training_samples)} training samples")
    
    # Prepare datasets
    if args.format in ["trocr", "both"]:
        print("\nPreparing TrOCR dataset...")
        trocr_path = preparator.prepare_trocr_dataset(training_samples)
        if args.split:
            preparator.split_dataset(str(trocr_path))
    
    if args.format in ["donut", "both"]:
        print("\nPreparing Donut dataset...")
        donut_path = preparator.prepare_donut_dataset(training_samples)
        if args.split:
            preparator.split_dataset(str(donut_path))
    
    print("\n✅ Data preparation complete!")


if __name__ == "__main__":
    main()

