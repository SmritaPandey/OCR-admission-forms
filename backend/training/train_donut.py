"""
Donut Fine-tuning Script
Fine-tune Donut model on custom form dataset

Donut (Document Understanding Transformer) is better for structured form understanding
with visual layout awareness.
"""
import argparse
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
import torch
from torch.utils.data import Dataset, DataLoader
from transformers import (
    DonutProcessor,
    VisionEncoderDecoderModel,
    Trainer,
    TrainingArguments,
    default_data_collator
)
from PIL import Image
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class DonutDataset(Dataset):
    """Dataset for Donut training"""
    
    def __init__(
        self,
        dataset_path: str,
        processor: DonutProcessor,
        max_length: int = 768,
        task_start_token: str = "<s_cord-v2>",
        eos_token: str = "</s>"
    ):
        """
        Args:
            dataset_path: Path to JSON file with {"image_path": "...", "ground_truth": "..."}
            processor: Donut processor for image/text preprocessing
            max_length: Maximum sequence length
            task_start_token: Task start token
            eos_token: End of sequence token
        """
        with open(dataset_path, 'r') as f:
            self.data = json.load(f)
        
        self.processor = processor
        self.max_length = max_length
        self.task_start_token = task_start_token
        self.eos_token = eos_token
    
    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, idx):
        item = self.data[idx]
        image_path = item['image_path']
        ground_truth = item.get('ground_truth', '{}')
        
        # Load image
        try:
            image = Image.open(image_path).convert('RGB')
        except Exception as e:
            print(f"Error loading image {image_path}: {e}")
            image = Image.new('RGB', (2560, 1920), color='white')
        
        # Process image
        pixel_values = self.processor(image, return_tensors="pt").pixel_values.squeeze()
        
        # Prepare text with task token
        text = f"{self.task_start_token}{ground_truth}{self.eos_token}"
        
        # Process text
        labels = self.processor.tokenizer(
            text,
            add_special_tokens=False,
            max_length=self.max_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt"
        ).input_ids.squeeze()
        
        return {
            'pixel_values': pixel_values,
            'labels': labels
        }


def train_donut(
    training_data_path: str,
    output_model_path: str,
    epochs: int = 15,
    batch_size: int = 4,
    learning_rate: float = 3e-5,
    val_data_path: Optional[str] = None,
    base_model: str = "naver-clova-ix/donut-base",
    max_length: int = 768,
    save_steps: int = 500,
    eval_steps: int = 500,
    logging_steps: int = 100
):
    """
    Fine-tune Donut model on form dataset
    
    Args:
        training_data_path: Path to training JSON file
        output_model_path: Path to save fine-tuned model
        epochs: Number of training epochs
        batch_size: Training batch size (smaller for Donut due to memory)
        learning_rate: Learning rate
        val_data_path: Optional validation dataset path
        base_model: Base Donut model to fine-tune
        max_length: Maximum sequence length
        save_steps: Steps between checkpoints
        eval_steps: Steps between evaluations
        logging_steps: Steps between logging
    """
    print("=" * 60)
    print("Donut Fine-tuning")
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
        print("⚠️  Warning: Donut training on CPU is very slow. GPU highly recommended.")
    print()
    
    # Load processor and model
    print("Loading Donut processor and model...")
    processor = DonutProcessor.from_pretrained(base_model)
    model = VisionEncoderDecoderModel.from_pretrained(base_model)
    
    # Move model to device
    model.to(device)
    print(f"✅ Model loaded: {base_model}")
    print(f"   Parameters: {sum(p.numel() for p in model.parameters()):,}")
    print()
    
    # Load datasets
    print("Loading training dataset...")
    train_dataset = DonutDataset(training_data_path, processor, max_length)
    print(f"✅ Training samples: {len(train_dataset)}")
    
    eval_dataset = None
    if val_data_path and os.path.exists(val_data_path):
        print("Loading validation dataset...")
        eval_dataset = DonutDataset(val_data_path, processor, max_length)
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
        save_total_limit=3,
        load_best_model_at_end=True if eval_dataset else False,
        metric_for_best_model="loss" if eval_dataset else None,
        greater_is_better=False,
        push_to_hub=False,
        report_to="none",
        fp16=torch.cuda.is_available(),  # Use mixed precision if GPU available
        gradient_accumulation_steps=2 if batch_size < 4 else 1  # Accumulate gradients for small batches
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
    print(f"  from transformers import DonutProcessor, VisionEncoderDecoderModel")
    print(f"  model = VisionEncoderDecoderModel.from_pretrained('{final_model_dir}')")
    print(f"  processor = DonutProcessor.from_pretrained('{final_model_dir}')")
    
    return final_model_dir


def main():
    """CLI interface"""
    parser = argparse.ArgumentParser(description="Fine-tune Donut model on form dataset")
    parser.add_argument("training_data", help="Path to training JSON file")
    parser.add_argument("output_model", help="Path to save fine-tuned model")
    parser.add_argument("--val-data", help="Path to validation JSON file")
    parser.add_argument("--epochs", type=int, default=15, help="Number of epochs")
    parser.add_argument("--batch-size", type=int, default=4, help="Batch size (smaller for Donut)")
    parser.add_argument("--learning-rate", type=float, default=3e-5, help="Learning rate")
    parser.add_argument("--base-model", default="naver-clova-ix/donut-base",
                       help="Base Donut model")
    parser.add_argument("--max-length", type=int, default=768, help="Max sequence length")
    parser.add_argument("--save-steps", type=int, default=500, help="Steps between checkpoints")
    parser.add_argument("--eval-steps", type=int, default=500, help="Steps between evaluations")
    
    args = parser.parse_args()
    
    train_donut(
        training_data_path=args.training_data,
        output_model_path=args.output_model,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        val_data_path=args.val_data,
        base_model=args.base_model,
        max_length=args.max_length,
        save_steps=args.save_steps,
        eval_steps=args.eval_steps
    )


if __name__ == "__main__":
    main()
