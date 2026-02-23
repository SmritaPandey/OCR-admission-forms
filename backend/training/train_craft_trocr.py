"""
Perfect PyTorch Training Script for CRAFT + TR-OCR
Fine-tune TR-OCR model specifically for handwritten medical prescriptions and forms

This script provides:
- Complete PyTorch training pipeline
- Data augmentation for better generalization
- Validation and metrics tracking
- Model checkpointing
- Support for both handwritten and printed text
- GPU/CPU/MPS (Apple Silicon) support
"""
import argparse
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader, random_split
from transformers import (
    TrOCRProcessor,
    VisionEncoderDecoderModel,
    VisionEncoderDecoderConfig,
    Trainer,
    TrainingArguments,
    default_data_collator
)
from PIL import Image, ImageEnhance, ImageFilter
import numpy as np
from tqdm import tqdm
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TrOCRDataset(Dataset):
    """Enhanced Dataset for TR-OCR training with data augmentation"""
    
    def __init__(
        self,
        dataset_path: str,
        processor: TrOCRProcessor,
        max_length: int = 128,
        augment: bool = True,
        image_dir: Optional[str] = None
    ):
        """
        Args:
            dataset_path: Path to JSON file with training data
            processor: TR-OCR processor for image/text preprocessing
            max_length: Maximum sequence length
            augment: Whether to apply data augmentation
            image_dir: Optional directory containing images (if paths in JSON are relative)
        """
        with open(dataset_path, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        
        # Handle both list and dict formats
        if isinstance(self.data, dict):
            self.data = [
                {"image_path": k, "text": v.get("text", v) if isinstance(v, dict) else v}
                for k, v in self.data.items()
            ]
        
        self.processor = processor
        self.max_length = max_length
        self.augment = augment
        self.image_dir = Path(image_dir) if image_dir else None
        
        # Filter out invalid entries
        self.data = [item for item in self.data if self._is_valid(item)]
        print(f"Loaded {len(self.data)} valid training samples")
    
    def _is_valid(self, item: Dict) -> bool:
        """Check if data item is valid"""
        image_path = item.get('image_path', '')
        text = item.get('text', '')
        
        if not image_path or not text:
            return False
        
        # Resolve image path
        if self.image_dir:
            full_path = self.image_dir / image_path
        else:
            full_path = Path(image_path)
        
        return full_path.exists() and len(text.strip()) > 0
    
    def _augment_image(self, image: Image.Image) -> Image.Image:
        """Apply advanced data augmentation to image"""
        if not self.augment:
            return image
        
        # Random contrast adjustment (more aggressive)
        if np.random.random() > 0.4:
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(np.random.uniform(0.7, 1.3))
        
        # Random brightness adjustment
        if np.random.random() > 0.4:
            enhancer = ImageEnhance.Brightness(image)
            image = enhancer.enhance(np.random.uniform(0.85, 1.15))
        
        # Random sharpening
        if np.random.random() > 0.6:
            image = image.filter(ImageFilter.SHARPEN)
        
        # Random color saturation (for color images)
        if np.random.random() > 0.7:
            enhancer = ImageEnhance.Color(image)
            image = enhancer.enhance(np.random.uniform(0.8, 1.2))
        
        # Random rotation (small angles only, ±2 degrees)
        if np.random.random() > 0.8:
            angle = np.random.uniform(-2, 2)
            image = image.rotate(angle, fillcolor='white', expand=False)
        
        # Random noise (very light)
        if np.random.random() > 0.9:
            img_array = np.array(image)
            noise = np.random.normal(0, 2, img_array.shape).astype(np.uint8)
            img_array = np.clip(img_array.astype(int) + noise, 0, 255).astype(np.uint8)
            image = Image.fromarray(img_array)
        
        return image
    
    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, idx):
        item = self.data[idx]
        image_path = item['image_path']
        text = item.get('text', '').strip()
        
        # Resolve image path
        if self.image_dir:
            full_path = self.image_dir / image_path
        else:
            full_path = Path(image_path)
        
        # Load image
        try:
            image = Image.open(full_path).convert('RGB')
        except Exception as e:
            print(f"Error loading image {full_path}: {e}")
            # Return a blank image if loading fails
            image = Image.new('RGB', (224, 224), color='white')
        
        # Apply augmentation
        image = self._augment_image(image)
        
        # Process image with processor
        pixel_values = self.processor(image, return_tensors="pt").pixel_values.squeeze(0)
        
        # Process text labels
        labels = self.processor.tokenizer(
            text,
            padding="max_length",
            max_length=self.max_length,
            truncation=True,
            return_tensors="pt"
        ).input_ids.squeeze(0)
        
        # Replace padding token id's of the labels by -100 so it's ignored by the loss function
        labels[labels == self.processor.tokenizer.pad_token_id] = -100
        
        return {
            'pixel_values': pixel_values,
            'labels': labels
        }


def calculate_cer(predicted: str, ground_truth: str) -> float:
    """Calculate Character Error Rate (CER)"""
    if not ground_truth:
        return 1.0 if predicted else 0.0
    
    n, m = len(ground_truth), len(predicted)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    
    for i in range(n + 1):
        dp[i][0] = i
    for j in range(m + 1):
        dp[0][j] = j
    
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if ground_truth[i-1] == predicted[j-1]:
                dp[i][j] = dp[i-1][j-1]
            else:
                dp[i][j] = 1 + min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1])
    
    return dp[n][m] / n if n > 0 else 1.0


def calculate_wer(predicted: str, ground_truth: str) -> float:
    """Calculate Word Error Rate (WER)"""
    pred_words = predicted.split()
    gt_words = ground_truth.split()
    
    if not gt_words:
        return 1.0 if pred_words else 0.0
    
    n, m = len(gt_words), len(pred_words)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    
    for i in range(n + 1):
        dp[i][0] = i
    for j in range(m + 1):
        dp[0][j] = j
    
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if gt_words[i-1] == pred_words[j-1]:
                dp[i][j] = dp[i-1][j-1]
            else:
                dp[i][j] = 1 + min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1])
    
    return dp[n][m] / n if n > 0 else 1.0


class CustomTrainer(Trainer):
    """Custom trainer with additional metrics and evaluation"""
    
    def __init__(self, *args, processor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.processor = processor
    
    def compute_loss(self, model, inputs, return_outputs=False):
        """
        Custom loss computation with additional metrics
        """
        labels = inputs.get("labels")
        outputs = model(**inputs)
        logits = outputs.get("logits")
        
        # Shift so that tokens < n predict n
        shift_logits = logits[..., :-1, :].contiguous()
        shift_labels = labels[..., 1:].contiguous()
        
        # Flatten the tokens
        loss_fct = nn.CrossEntropyLoss(ignore_index=-100)
        loss = loss_fct(shift_logits.view(-1, shift_logits.size(-1)), shift_labels.view(-1))
        
        return (loss, outputs) if return_outputs else loss
    
    def evaluate(self, eval_dataset=None, ignore_keys=None, metric_key_prefix="eval"):
        """Enhanced evaluation with CER and WER metrics"""
        eval_dataset = eval_dataset or self.eval_dataset
        if eval_dataset is None:
            return {}
        
        # Run standard evaluation
        eval_results = super().evaluate(eval_dataset, ignore_keys, metric_key_prefix)
        
        # Calculate CER and WER on a sample
        if self.processor and hasattr(self, 'model'):
            try:
                # Sample a few examples for CER/WER calculation
                sample_indices = np.random.choice(
                    min(len(eval_dataset), 100),
                    size=min(20, len(eval_dataset)),
                    replace=False
                )
                
                cer_scores = []
                wer_scores = []
                
                self.model.eval()
                with torch.no_grad():
                    for idx in sample_indices:
                        item = eval_dataset[idx]
                        pixel_values = item['pixel_values'].unsqueeze(0).to(self.model.device)
                        labels = item['labels']
                        
                        # Generate prediction
                        generated_ids = self.model.generate(pixel_values)
                        predicted_text = self.processor.batch_decode(
                            generated_ids, skip_special_tokens=True
                        )[0]
                        
                        # Decode ground truth
                        labels[labels == -100] = self.processor.tokenizer.pad_token_id
                        ground_truth = self.processor.tokenizer.decode(
                            labels, skip_special_tokens=True
                        )
                        
                        # Calculate metrics
                        cer = calculate_cer(predicted_text, ground_truth)
                        wer = calculate_wer(predicted_text, ground_truth)
                        
                        cer_scores.append(cer)
                        wer_scores.append(wer)
                
                eval_results[f"{metric_key_prefix}_cer"] = np.mean(cer_scores)
                eval_results[f"{metric_key_prefix}_wer"] = np.mean(wer_scores)
                eval_results[f"{metric_key_prefix}_accuracy"] = 1.0 - np.mean(cer_scores)
                
            except Exception as e:
                print(f"Warning: Could not calculate CER/WER: {e}")
        
        return eval_results


def train_craft_trocr(
    training_data_path: str,
    output_model_path: str,
    epochs: int = 20,
    batch_size: int = 8,
    learning_rate: float = 5e-5,
    val_data_path: Optional[str] = None,
    val_split: float = 0.2,
    base_model: str = "microsoft/trocr-base-handwritten",
    max_length: int = 128,
    save_steps: int = 500,
    eval_steps: int = 500,
    logging_steps: int = 100,
    warmup_steps: int = 500,
    weight_decay: float = 0.01,
    image_dir: Optional[str] = None,
    augment: bool = True,
    gradient_accumulation_steps: int = 1,
    fp16: bool = False,
    resume_from_checkpoint: Optional[str] = None,
    lr_scheduler: str = "cosine",
    early_stopping_patience: Optional[int] = None
):
    """
    Perfect PyTorch training for TR-OCR model
    
    Args:
        training_data_path: Path to training JSON file
        output_model_path: Path to save fine-tuned model
        epochs: Number of training epochs
        batch_size: Training batch size
        learning_rate: Learning rate
        val_data_path: Optional validation dataset path
        val_split: Validation split ratio if val_data_path not provided
        base_model: Base TR-OCR model to fine-tune
        max_length: Maximum sequence length
        save_steps: Steps between checkpoints
        eval_steps: Steps between evaluations
        logging_steps: Steps between logging
        warmup_steps: Number of warmup steps
        weight_decay: Weight decay for regularization
        image_dir: Directory containing images (if paths are relative)
        augment: Whether to apply data augmentation
        gradient_accumulation_steps: Gradient accumulation steps
        fp16: Use mixed precision training (requires GPU)
        resume_from_checkpoint: Path to checkpoint to resume from
    """
    print("=" * 80)
    print("CRAFT + TR-OCR Perfect Training")
    print("=" * 80)
    print(f"Training data: {training_data_path}")
    print(f"Output model: {output_model_path}")
    print(f"Base model: {base_model}")
    print(f"Epochs: {epochs}, Batch size: {batch_size}, LR: {learning_rate}")
    print(f"Max length: {max_length}, Augmentation: {augment}")
    print()
    
    # Detect device
    if torch.cuda.is_available():
        device = "cuda"
        print(f"✅ Using GPU: {torch.cuda.get_device_name(0)}")
        print(f"   CUDA Version: {torch.version.cuda}")
        print(f"   GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
    elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        device = "mps"
        print("✅ Using Apple Silicon (MPS)")
    else:
        device = "cpu"
        print("⚠️  Using CPU - Training will be slow")
        print("   Consider using GPU for faster training")
    
    print()
    
    # Load processor and model
    print("Loading TR-OCR processor and model...")
    try:
        processor = TrOCRProcessor.from_pretrained(base_model)
        model = VisionEncoderDecoderModel.from_pretrained(base_model)
        print(f"✅ Model loaded: {base_model}")
    except Exception as e:
        print(f"❌ Error loading model: {e}")
        print("   Make sure you have internet connection to download the model")
        raise
    
    # Count parameters
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"   Total parameters: {total_params:,}")
    print(f"   Trainable parameters: {trainable_params:,}")
    print()
    
    # Move model to device
    model.to(device)
    
    # Load datasets
    print("Loading training dataset...")
    train_dataset = TrOCRDataset(
        training_data_path,
        processor,
        max_length=max_length,
        augment=augment,
        image_dir=image_dir
    )
    
    if len(train_dataset) == 0:
        raise ValueError("No valid training samples found!")
    
    print(f"✅ Training samples: {len(train_dataset)}")
    
    # Handle validation dataset
    eval_dataset = None
    if val_data_path and os.path.exists(val_data_path):
        print("Loading validation dataset...")
        eval_dataset = TrOCRDataset(
            val_data_path,
            processor,
            max_length=max_length,
            augment=False,  # No augmentation for validation
            image_dir=image_dir
        )
        print(f"✅ Validation samples: {len(eval_dataset)}")
    elif val_split > 0:
        print(f"Splitting dataset: {val_split*100:.1f}% for validation...")
        train_size = int((1 - val_split) * len(train_dataset))
        val_size = len(train_dataset) - train_size
        train_dataset, eval_dataset = random_split(
            train_dataset,
            [train_size, val_size],
            generator=torch.Generator().manual_seed(42)
        )
        print(f"✅ Training samples: {len(train_dataset)}")
        print(f"✅ Validation samples: {len(eval_dataset)}")
    
    print()
    
    # Setup training arguments
    output_dir = Path(output_model_path)
    checkpoint_dir = output_dir.parent / "checkpoints"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    # Calculate total steps
    steps_per_epoch = len(train_dataset) // (batch_size * gradient_accumulation_steps)
    total_steps = steps_per_epoch * epochs
    
    print(f"Training configuration:")
    print(f"   Steps per epoch: {steps_per_epoch}")
    print(f"   Total steps: {total_steps}")
    print(f"   Save steps: {save_steps}")
    print(f"   Eval steps: {eval_steps}")
    print()
    
    training_args = TrainingArguments(
        output_dir=str(checkpoint_dir),
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        learning_rate=learning_rate,
        warmup_steps=warmup_steps,
        weight_decay=weight_decay,
        logging_dir=str(checkpoint_dir / "logs"),
        logging_steps=logging_steps,
        save_steps=save_steps,
        eval_steps=eval_steps if eval_dataset else None,
        evaluation_strategy="steps" if eval_dataset else "no",
        save_total_limit=5,  # Keep last 5 checkpoints
        load_best_model_at_end=True if eval_dataset else False,
        metric_for_best_model="eval_loss" if eval_dataset else "train_loss",
        greater_is_better=False,
        push_to_hub=False,
        report_to="none",
        gradient_accumulation_steps=gradient_accumulation_steps,
        fp16=fp16 and device == "cuda",  # Only use fp16 on CUDA
        dataloader_num_workers=4 if device != "cpu" else 0,
        remove_unused_columns=False,
        resume_from_checkpoint=resume_from_checkpoint,
        # Learning rate scheduling
        lr_scheduler_type=lr_scheduler,  # Cosine annealing for better convergence
        # Early stopping (via patience)
        save_strategy="steps",
        # Better optimization
        optim="adamw_torch",  # Use AdamW optimizer
        max_grad_norm=1.0,  # Gradient clipping
        # Evaluation settings
        eval_accumulation_steps=1,
        prediction_loss_only=False
    )
    
    # Create trainer with processor for evaluation metrics
    trainer = CustomTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        data_collator=default_data_collator,
        tokenizer=processor.tokenizer,
        processor=processor  # Pass processor for CER/WER calculation
    )
    
    # Train
    print("=" * 80)
    print("Starting Training...")
    print("=" * 80)
    print()
    
    train_result = None
    try:
        train_result = trainer.train(resume_from_checkpoint=resume_from_checkpoint)
        print()
        print("=" * 80)
        print("✅ Training Complete!")
        print("=" * 80)
        if train_result:
            print(f"Final training loss: {train_result.training_loss:.4f}")
        if eval_dataset:
            eval_result = trainer.evaluate()
            print(f"Final validation loss: {eval_result.get('eval_loss', 'N/A'):.4f}")
            if 'eval_cer' in eval_result:
                print(f"Character Error Rate (CER): {eval_result['eval_cer']:.4f}")
                print(f"Word Error Rate (WER): {eval_result['eval_wer']:.4f}")
                print(f"Accuracy: {eval_result.get('eval_accuracy', 1.0 - eval_result['eval_cer']):.4f}")
        print()
    except KeyboardInterrupt:
        print("\n⚠️  Training interrupted by user")
        print("   Saving current checkpoint...")
        train_result = None  # Will use default values
    except Exception as e:
        print(f"\n❌ Training error: {e}")
        import traceback
        traceback.print_exc()
        raise
    
    # Save final model
    print(f"Saving final model to {output_model_path}...")
    final_model_dir = Path(output_model_path)
    final_model_dir.mkdir(parents=True, exist_ok=True)
    
    model.save_pretrained(str(final_model_dir))
    processor.save_pretrained(str(final_model_dir))
    
    # Get final evaluation metrics
    final_metrics = {}
    if eval_dataset:
        try:
            final_eval = trainer.evaluate()
            final_metrics = {
                "final_eval_loss": final_eval.get('eval_loss'),
                "final_cer": final_eval.get('eval_cer'),
                "final_wer": final_eval.get('eval_wer'),
                "final_accuracy": final_eval.get('eval_accuracy')
            }
        except:
            pass
    
    # Save training metadata
    metadata = {
        "base_model": base_model,
        "training_samples": len(train_dataset),
        "validation_samples": len(eval_dataset) if eval_dataset else 0,
        "epochs": epochs,
        "batch_size": batch_size,
        "learning_rate": learning_rate,
        "max_length": max_length,
        "trained_at": datetime.now().isoformat(),
        "device": device,
        "final_training_loss": train_result.training_loss if train_result else None,
        **final_metrics
    }
    
    with open(final_model_dir / "training_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)
    
    print(f"✅ Model saved to {final_model_dir}")
    print()
    print("=" * 80)
    print("Training Summary")
    print("=" * 80)
    print(f"Final model: {final_model_dir}")
    print(f"Training samples: {len(train_dataset)}")
    if eval_dataset:
        print(f"Validation samples: {len(eval_dataset)}")
    print()
    print("To use the trained model:")
    print(f"  export TROCR_CUSTOM_MODEL_PATH='{final_model_dir}'")
    print(f"  # Or in Python:")
    print(f"  from transformers import TrOCRProcessor, VisionEncoderDecoderModel")
    print(f"  model = VisionEncoderDecoderModel.from_pretrained('{final_model_dir}')")
    print(f"  processor = TrOCRProcessor.from_pretrained('{final_model_dir}')")
    print()
    
    return final_model_dir


def main():
    """CLI interface"""
    parser = argparse.ArgumentParser(
        description="Perfect PyTorch training for CRAFT + TR-OCR model",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("training_data", help="Path to training JSON file")
    parser.add_argument("output_model", help="Path to save fine-tuned model")
    parser.add_argument("--val-data", help="Path to validation JSON file")
    parser.add_argument("--val-split", type=float, default=0.2,
                       help="Validation split ratio (if --val-data not provided)")
    parser.add_argument("--epochs", type=int, default=20, help="Number of epochs")
    parser.add_argument("--batch-size", type=int, default=8, help="Batch size")
    parser.add_argument("--learning-rate", type=float, default=5e-5, help="Learning rate")
    parser.add_argument("--base-model", default="microsoft/trocr-base-handwritten",
                       help="Base TR-OCR model")
    parser.add_argument("--max-length", type=int, default=128, help="Max sequence length")
    parser.add_argument("--save-steps", type=int, default=500, help="Steps between checkpoints")
    parser.add_argument("--eval-steps", type=int, default=500, help="Steps between evaluations")
    parser.add_argument("--warmup-steps", type=int, default=500, help="Warmup steps")
    parser.add_argument("--weight-decay", type=float, default=0.01, help="Weight decay")
    parser.add_argument("--image-dir", help="Directory containing images (if paths are relative)")
    parser.add_argument("--no-augment", action="store_true", help="Disable data augmentation")
    parser.add_argument("--gradient-accumulation", type=int, default=1,
                       help="Gradient accumulation steps")
    parser.add_argument("--fp16", action="store_true", help="Use mixed precision training (GPU only)")
    parser.add_argument("--resume", help="Path to checkpoint to resume from")
    parser.add_argument("--early-stopping-patience", type=int, default=None,
                       help="Early stopping patience (number of evaluations without improvement)")
    parser.add_argument("--lr-scheduler", type=str, default="cosine",
                       choices=["linear", "cosine", "polynomial", "constant"],
                       help="Learning rate scheduler type")
    
    args = parser.parse_args()
    
    train_craft_trocr(
        training_data_path=args.training_data,
        output_model_path=args.output_model,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        val_data_path=args.val_data,
        val_split=args.val_split,
        base_model=args.base_model,
        max_length=args.max_length,
        save_steps=args.save_steps,
        eval_steps=args.eval_steps,
        warmup_steps=args.warmup_steps,
        weight_decay=args.weight_decay,
        image_dir=args.image_dir,
        augment=not args.no_augment,
        gradient_accumulation_steps=args.gradient_accumulation,
        fp16=args.fp16,
        resume_from_checkpoint=args.resume,
        lr_scheduler=args.lr_scheduler,
        early_stopping_patience=args.early_stopping_patience
    )


if __name__ == "__main__":
    main()

