"""
CRAFT + TrOCR Training Script
Complete training pipeline inspired by Azure Intelligent Form Labeling

Features:
- Automatic data preparation from annotations
- Progressive training (start with base model, fine-tune incrementally)
- Continuous improvement (retrain on corrections)
- Model evaluation and metrics
- Checkpoint management
"""
import argparse
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
import torch
from torch.utils.data import Dataset, DataLoader
from transformers import (
    TrOCRProcessor,
    VisionEncoderDecoderModel,
    Trainer,
    TrainingArguments,
    default_data_collator
)
from PIL import Image
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.config import settings


class CraftTrocrDataset(Dataset):
    """Dataset for CRAFT+TrOCR training with region-level annotations"""
    
    def __init__(
        self,
        dataset_path: str,
        processor: TrOCRProcessor,
        max_length: int = 128,
        use_regions: bool = True
    ):
        """
        Args:
            dataset_path: Path to JSON file with training data
            processor: TrOCR processor for image/text preprocessing
            max_length: Maximum sequence length
            use_regions: If True, use region-level annotations (CRAFT-style)
        """
        with open(dataset_path, 'r') as f:
            self.data = json.load(f)
        
        self.processor = processor
        self.max_length = max_length
        self.use_regions = use_regions
    
    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, idx):
        item = self.data[idx]
        
        # Handle both full-image and region-level data
        if self.use_regions and 'regions' in item:
            # Use first region or combine regions
            regions = item['regions']
            if regions:
                # Use first region for now (can be extended to use all)
                region = regions[0]
                image_path = region.get('image_path', item.get('image_path', ''))
                text = region.get('text', item.get('text', ''))
            else:
                image_path = item.get('image_path', '')
                text = item.get('text', '')
        else:
            image_path = item.get('image_path', '')
            text = item.get('text', '')
        
        # Load image
        try:
            if not os.path.exists(image_path):
                # Try relative path
                image_path = str(Path(settings.UPLOAD_DIR) / image_path)
            
            image = Image.open(image_path).convert('RGB')
        except Exception as e:
            print(f"Error loading image {image_path}: {e}")
            # Return a blank image if loading fails
            image = Image.new('RGB', (224, 224), color='white')
        
        # Process image and text
        pixel_values = self.processor(image, return_tensors="pt").pixel_values.squeeze()
        
        # Process text
        labels = self.processor.tokenizer(
            text,
            padding="max_length",
            max_length=self.max_length,
            truncation=True,
            return_tensors="pt"
        ).input_ids.squeeze()
        
        return {
            'pixel_values': pixel_values,
            'labels': labels
        }


def train_craft_trocr(
    training_data_path: str,
    output_model_path: str,
    epochs: int = 10,
    batch_size: int = 8,
    learning_rate: float = 5e-5,
    val_data_path: Optional[str] = None,
    base_model: str = "microsoft/trocr-base-handwritten",
    max_length: int = 128,
    save_steps: int = 500,
    eval_steps: int = 500,
    logging_steps: int = 100,
    use_regions: bool = True,
    resume_from_checkpoint: Optional[str] = None
):
    """
    Train CRAFT+TrOCR model on form dataset
    
    Args:
        training_data_path: Path to training JSON file
        output_model_path: Path to save fine-tuned model
        epochs: Number of training epochs
        batch_size: Training batch size
        learning_rate: Learning rate
        val_data_path: Optional validation dataset path
        base_model: Base TrOCR model to fine-tune
        max_length: Maximum sequence length
        save_steps: Steps between checkpoints
        eval_steps: Steps between evaluations
        logging_steps: Steps between logging
        use_regions: Use region-level annotations (CRAFT-style)
        resume_from_checkpoint: Path to checkpoint to resume from
    """
    print("=" * 60)
    print("CRAFT + TrOCR Training")
    print("=" * 60)
    print(f"Training data: {training_data_path}")
    print(f"Output model: {output_model_path}")
    print(f"Base model: {base_model}")
    print(f"Epochs: {epochs}, Batch size: {batch_size}, LR: {learning_rate}")
    print()
    
    # Check for GPU
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    if device == "cpu":
        print("⚠️  Warning: Training on CPU will be slow. Consider using GPU.")
    print()
    
    # Load processor and model
    print("Loading TrOCR processor and model...")
    
    if resume_from_checkpoint and os.path.exists(resume_from_checkpoint):
        print(f"Resuming from checkpoint: {resume_from_checkpoint}")
        processor = TrOCRProcessor.from_pretrained(resume_from_checkpoint)
        model = VisionEncoderDecoderModel.from_pretrained(resume_from_checkpoint)
    else:
        processor = TrOCRProcessor.from_pretrained(base_model)
        model = VisionEncoderDecoderModel.from_pretrained(base_model)
    
    # Move model to device
    model.to(device)
    print(f"✅ Model loaded: {base_model}")
    print(f"   Parameters: {sum(p.numel() for p in model.parameters()):,}")
    print()
    
    # Load datasets
    print("Loading training dataset...")
    train_dataset = CraftTrocrDataset(training_data_path, processor, max_length, use_regions)
    print(f"✅ Training samples: {len(train_dataset)}")
    
    eval_dataset = None
    if val_data_path and os.path.exists(val_data_path):
        print("Loading validation dataset...")
        eval_dataset = CraftTrocrDataset(val_data_path, processor, max_length, use_regions)
        print(f"✅ Validation samples: {len(eval_dataset)}")
    print()
    
    # Setup training arguments
    output_dir = Path(output_model_path).parent / "checkpoints"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    training_args = TrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        learning_rate=learning_rate,
        warmup_steps=500,
        weight_decay=0.01,
        logging_dir=str(output_dir / "logs"),
        logging_steps=logging_steps,
        save_steps=save_steps,
        eval_steps=eval_steps if eval_dataset else None,
        evaluation_strategy="steps" if eval_dataset else "no",
        save_total_limit=5,  # Keep more checkpoints for continuous improvement
        load_best_model_at_end=True if eval_dataset else False,
        metric_for_best_model="loss" if eval_dataset else None,
        greater_is_better=False,
        push_to_hub=False,
        report_to="none",
        fp16=device == "cuda",  # Use mixed precision on GPU
        dataloader_num_workers=4 if device == "cuda" else 0,
        gradient_accumulation_steps=2,  # Effective batch size = batch_size * 2
    )
    
    # Create trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        data_collator=default_data_collator,
        tokenizer=processor.tokenizer
    )
    
    # Train
    print("Starting training...")
    print("-" * 60)
    
    if resume_from_checkpoint:
        trainer.train(resume_from_checkpoint=resume_from_checkpoint)
    else:
        trainer.train()
    
    print("-" * 60)
    print("✅ Training complete!")
    print()
    
    # Save final model
    print(f"Saving model to {output_model_path}...")
    final_model_dir = Path(output_model_path)
    final_model_dir.mkdir(parents=True, exist_ok=True)
    
    model.save_pretrained(str(final_model_dir))
    processor.save_pretrained(str(final_model_dir))
    
    # Save training metadata
    metadata = {
        "base_model": base_model,
        "training_samples": len(train_dataset),
        "validation_samples": len(eval_dataset) if eval_dataset else 0,
        "epochs": epochs,
        "batch_size": batch_size,
        "learning_rate": learning_rate,
        "trained_at": datetime.utcnow().isoformat(),
        "use_regions": use_regions
    }
    
    with open(final_model_dir / "training_metadata.json", 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"✅ Model saved to {final_model_dir}")
    print()
    print("=" * 60)
    print("Training Summary")
    print("=" * 60)
    print(f"Final model: {final_model_dir}")
    print(f"Training samples: {len(train_dataset)}")
    if eval_dataset:
        print(f"Validation samples: {len(eval_dataset)}")
    print()
    print("To use the trained model:")
    print(f"  Set TROCR_CUSTOM_MODEL_PATH={final_model_dir} in .env")
    
    return final_model_dir


def main():
    """CLI interface"""
    parser = argparse.ArgumentParser(
        description="Train CRAFT+TrOCR model on form dataset"
    )
    parser.add_argument("training_data", help="Path to training JSON file")
    parser.add_argument("output_model", help="Path to save fine-tuned model")
    parser.add_argument("--val-data", help="Path to validation JSON file")
    parser.add_argument("--epochs", type=int, default=10, help="Number of epochs")
    parser.add_argument("--batch-size", type=int, default=8, help="Batch size")
    parser.add_argument("--learning-rate", type=float, default=5e-5, help="Learning rate")
    parser.add_argument("--base-model", default="microsoft/trocr-base-handwritten",
                       help="Base TrOCR model")
    parser.add_argument("--max-length", type=int, default=128, help="Max sequence length")
    parser.add_argument("--save-steps", type=int, default=500, help="Steps between checkpoints")
    parser.add_argument("--eval-steps", type=int, default=500, help="Steps between evaluations")
    parser.add_argument("--resume-from", help="Path to checkpoint to resume from")
    parser.add_argument("--no-regions", action="store_true", 
                       help="Don't use region-level annotations")
    
    args = parser.parse_args()
    
    train_craft_trocr(
        training_data_path=args.training_data,
        output_model_path=args.output_model,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        val_data_path=args.val_data,
        base_model=args.base_model,
        max_length=args.max_length,
        save_steps=args.save_steps,
        eval_steps=args.eval_steps,
        use_regions=not args.no_regions,
        resume_from_checkpoint=args.resume_from
    )


if __name__ == "__main__":
    main()
