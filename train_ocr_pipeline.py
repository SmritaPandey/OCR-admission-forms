"""
OCR Training Pipeline — Master Training Script

3-Stage Training:
  Stage 1: Fine-tune TrOCR on admission form images
  Stage 2: Enhance Tesseract with custom wordlists & training data
  Stage 3: Build ensemble OCR combining the best models

Usage:
  python train_ocr_pipeline.py                             # Full training
  python train_ocr_pipeline.py --epochs 1 --max-samples 5  # Quick test
  python train_ocr_pipeline.py --stage 1                   # TrOCR only
  python train_ocr_pipeline.py --stage 2                   # Tesseract only
  python train_ocr_pipeline.py --stage 3                   # Ensemble config only
"""

import json
import os
import sys
import argparse
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

PROJECT_ROOT = Path(__file__).parent
DEFAULT_DATA_DIR = PROJECT_ROOT / "training_data" / "prepared"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "training_output" / "models"

# ============================================================
# Stage 1: TrOCR Fine-Tuning
# ============================================================
def train_trocr(
    data_dir: Path,
    output_dir: Path,
    base_model: str = "microsoft/trocr-base-handwritten",
    epochs: int = 20,
    batch_size: int = 8,
    learning_rate: float = 5e-5,
    max_samples: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Fine-tune TrOCR on admission form images.
    
    Uses HuggingFace Transformers Trainer with a VisionEncoderDecoderModel.
    """
    print("\n" + "=" * 70)
    print("  Stage 1: TrOCR Fine-Tuning")
    print("=" * 70)

    # --- Check dependencies ---
    try:
        import torch
        from transformers import (
            TrOCRProcessor,
            VisionEncoderDecoderModel,
            Seq2SeqTrainer,
            Seq2SeqTrainingArguments,
            default_data_collator,
        )
        from PIL import Image
        print(f"  ✓ PyTorch {torch.__version__}")
        print(f"  ✓ Device: {'cuda' if torch.cuda.is_available() else 'cpu'}")
        if torch.cuda.is_available():
            print(f"    GPU: {torch.cuda.get_device_name(0)}")
    except ImportError as e:
        print(f"  ✗ Missing dependency: {e}")
        print("  Install: pip install torch transformers pillow")
        return {"status": "error", "message": str(e)}

    device = "cuda" if torch.cuda.is_available() else "cpu"

    # --- Load training data ---
    training_data_path = data_dir / "training_data.json"
    if not training_data_path.exists():
        print(f"  ✗ Training data not found: {training_data_path}")
        print("  Run: python prepare_all_training_data.py first")
        return {"status": "error", "message": "Training data not found"}

    with open(training_data_path, "r", encoding="utf-8") as f:
        all_records = json.load(f)

    # Filter records that have images and OCR text or field data
    train_records = []
    for rec in all_records:
        if rec.get("split") != "train":
            continue
        if not rec.get("images"):
            continue
        # Need either raw_ocr_text or field values as ground truth
        gt_text = rec.get("raw_ocr_text", "")
        if not gt_text and rec.get("fields"):
            # Build ground truth from fields
            gt_text = " | ".join(f"{k}: {v}" for k, v in rec["fields"].items())
        if gt_text:
            for img_path in rec["images"]:
                if Path(img_path).exists():
                    train_records.append({
                        "image_path": img_path,
                        "text": gt_text[:512],  # TrOCR max length
                    })

    val_records = []
    for rec in all_records:
        if rec.get("split") != "val":
            continue
        if not rec.get("images"):
            continue
        gt_text = rec.get("raw_ocr_text", "")
        if not gt_text and rec.get("fields"):
            gt_text = " | ".join(f"{k}: {v}" for k, v in rec["fields"].items())
        if gt_text:
            for img_path in rec["images"]:
                if Path(img_path).exists():
                    val_records.append({
                        "image_path": img_path,
                        "text": gt_text[:512],
                    })

    if max_samples:
        train_records = train_records[:max_samples]
        val_records = val_records[:max(1, max_samples // 5)]

    print(f"  Training samples: {len(train_records)}")
    print(f"  Validation samples: {len(val_records)}")

    if len(train_records) == 0:
        print("  ⚠ No training data with images available")
        print("  Make sure to run prepare_all_training_data.py with image conversion")
        return {"status": "skipped", "message": "No training samples with images"}

    # --- Load model & processor ---
    print(f"\n  Loading base model: {base_model} ...")
    processor = TrOCRProcessor.from_pretrained(base_model)
    model = VisionEncoderDecoderModel.from_pretrained(base_model)

    # Set decoder tokens
    model.config.decoder_start_token_id = processor.tokenizer.cls_token_id
    model.config.pad_token_id = processor.tokenizer.pad_token_id
    model.config.vocab_size = model.config.decoder.vocab_size
    model.config.eos_token_id = processor.tokenizer.sep_token_id
    model.config.max_length = 256
    model.config.early_stopping = True
    model.config.no_repeat_ngram_size = 3
    model.config.length_penalty = 2.0
    model.config.num_beams = 4

    print("  ✓ Model loaded")

    # --- Create PyTorch Dataset ---
    class OCRDataset(torch.utils.data.Dataset):
        def __init__(self, records, processor, max_target_length=256):
            self.records = records
            self.processor = processor
            self.max_target_length = max_target_length

        def __len__(self):
            return len(self.records)

        def __getitem__(self, idx):
            rec = self.records[idx]
            image = Image.open(rec["image_path"]).convert("RGB")
            
            # Process image
            pixel_values = self.processor(image, return_tensors="pt").pixel_values.squeeze()
            
            # Process text
            labels = self.processor.tokenizer(
                rec["text"],
                padding="max_length",
                max_length=self.max_target_length,
                truncation=True,
                return_tensors="pt",
            ).input_ids.squeeze()
            
            # Replace padding token id's of the labels by -100
            labels[labels == self.processor.tokenizer.pad_token_id] = -100

            return {
                "pixel_values": pixel_values,
                "labels": labels,
            }

    train_dataset = OCRDataset(train_records, processor)
    val_dataset = OCRDataset(val_records, processor) if val_records else None

    # --- Configure training ---
    trocr_output = output_dir / "trocr_finetuned"
    trocr_output.mkdir(parents=True, exist_ok=True)

    training_args = Seq2SeqTrainingArguments(
        output_dir=str(trocr_output),
        predict_with_generate=True,
        eval_strategy="epoch" if val_dataset else "no",
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        num_train_epochs=epochs,
        learning_rate=learning_rate,
        weight_decay=0.01,
        warmup_ratio=0.1,
        fp16=torch.cuda.is_available(),
        save_strategy="epoch",
        save_total_limit=3,
        logging_dir=str(trocr_output / "logs"),
        logging_steps=10,
        load_best_model_at_end=True if val_dataset else False,
        metric_for_best_model="eval_loss" if val_dataset else None,
        report_to="none",
        dataloader_num_workers=0,  # Windows compatibility
    )

    # --- Train ---
    print(f"\n  Starting training...")
    print(f"  Epochs: {epochs}, Batch size: {batch_size}, LR: {learning_rate}")
    print(f"  Output: {trocr_output}")
    print()

    trainer = Seq2SeqTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        tokenizer=processor.tokenizer,
        data_collator=default_data_collator,
    )

    start_time = time.time()
    train_result = trainer.train()
    training_time = time.time() - start_time

    # --- Save final model ---
    print(f"\n  Saving fine-tuned model to {trocr_output}...")
    trainer.save_model(str(trocr_output))
    processor.save_pretrained(str(trocr_output))

    # Save training metrics
    metrics = {
        "status": "success",
        "base_model": base_model,
        "training_time_seconds": training_time,
        "train_samples": len(train_records),
        "val_samples": len(val_records),
        "epochs": epochs,
        "batch_size": batch_size,
        "learning_rate": learning_rate,
        "device": device,
        "train_loss": train_result.training_loss,
        "model_path": str(trocr_output),
        "completed_at": datetime.now().isoformat(),
    }

    with open(trocr_output / "training_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    print(f"\n  ✅ TrOCR fine-tuning complete!")
    print(f"     Training loss: {train_result.training_loss:.4f}")
    print(f"     Time: {training_time:.1f}s")

    return metrics


# ============================================================
# Stage 2: Tesseract Enhancement
# ============================================================
def enhance_tesseract(
    data_dir: Path,
    output_dir: Path,
) -> Dict[str, Any]:
    """
    Enhance Tesseract OCR with custom wordlists and training data
    built from verified admission form fields.
    """
    print("\n" + "=" * 70)
    print("  Stage 2: Tesseract Enhancement")
    print("=" * 70)

    tesseract_dir = output_dir / "tesseract_enhanced"
    tesseract_dir.mkdir(parents=True, exist_ok=True)

    # --- Load training data for wordlist ---
    training_data_path = data_dir / "training_data.json"
    if not training_data_path.exists():
        print("  ✗ Training data not found")
        return {"status": "error", "message": "Training data not found"}

    with open(training_data_path, "r", encoding="utf-8") as f:
        all_records = json.load(f)

    # --- Build custom wordlists ---
    names = set()
    places = set()
    institutions = set()
    all_words = set()
    field_patterns = {}

    for rec in all_records:
        fields = rec.get("fields", {})
        for key, value in fields.items():
            if not value:
                continue
            words = value.split()
            all_words.update(w.strip() for w in words if len(w.strip()) > 1)

            # Categorize
            if any(k in key for k in ["name", "first_name", "surname", "middle_name"]):
                names.update(w.strip() for w in words if len(w.strip()) > 1)
            if any(k in key for k in ["state", "city", "address", "pincode"]):
                places.update(w.strip() for w in words if len(w.strip()) > 1)
            if any(k in key for k in ["institution", "school", "board", "organization"]):
                institutions.update(w.strip() for w in words if len(w.strip()) > 1)

            # Track field patterns
            if key not in field_patterns:
                field_patterns[key] = []
            field_patterns[key].append(value)

    # --- Write wordlists ---
    wordlist_path = tesseract_dir / "admission_forms.wordlist"
    with open(wordlist_path, "w", encoding="utf-8") as f:
        for word in sorted(all_words):
            f.write(word + "\n")

    names_path = tesseract_dir / "names.wordlist"
    common_names = [
        "NAVYA", "ARYAN", "KARAN", "DEVESH", "AYAN", "PRATHA", "SHUBHAM",
        "KRISHNA", "TANVIR", "KARNIKA", "RISHI", "SATVIKA", "SHANU",
        "CHANEK", "ADVAIT", "VAISHNAVI", "SPARSH", "DAKSH", "ADITYA",
        "ROOPASHEE", "KASHISH", "MEHAK", "RASHI", "MAANVI", "AKSHITA",
        "NEILANG", "SAKSHI", "SMITKUMAR", "SIYA", "ANKIT", "NIRAKSHA",
        "PARUL", "YUG", "NAVEEN", "SHOURAYA", "PRIYANSHU", "PRAGYA",
        "PRAGATI", "SHAURYA", "RADDHI", "DHRUV", "KUMAR", "SINGH",
        "SHARMA", "VERMA", "YADAV", "GUPTA", "PANDEY", "MISHRA",
        "AGARWAL", "GARG", "JAIN", "CHAUHAN", "BISHT", "SONI",
    ]
    with open(names_path, "w", encoding="utf-8") as f:
        for name in sorted(names):
            f.write(name + "\n")
        # Add common Indian names not already in the set
        for name in common_names:
            if name not in names:
                f.write(name + "\n")

    places_path = tesseract_dir / "places.wordlist"
    with open(places_path, "w", encoding="utf-8") as f:
        for place in sorted(places):
            f.write(place + "\n")
        # Add common Indian states/cities
        for place in ["DELHI", "MUMBAI", "KOLKATA", "CHENNAI", "BANGALORE",
                       "HYDERABAD", "PUNE", "JAIPUR", "LUCKNOW", "CHANDIGARH",
                       "HARYANA", "RAJASTHAN", "UTTAR PRADESH", "MADHYA PRADESH",
                       "BIHAR", "JHARKHAND", "UTTARAKHAND", "PUNJAB", "HIMACHAL"]:
            f.write(place + "\n")

    # --- Write Tesseract config ---
    config_path = tesseract_dir / "admission_form.config"
    with open(config_path, "w") as f:
        f.write("# Tesseract config for admission forms\n")
        f.write("tessedit_char_whitelist 0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz .,;:/()-@#&+\n")
        f.write(f"user_words_file {wordlist_path}\n")
        f.write("tessedit_pageseg_mode 6\n")  # Uniform block of text
        f.write("tessedit_ocr_engine_mode 3\n")  # Default + LSTM

    # --- Save field pattern data (for post-processing) ---
    patterns_path = tesseract_dir / "field_patterns.json"
    with open(patterns_path, "w", encoding="utf-8") as f:
        json.dump(field_patterns, f, indent=2, ensure_ascii=False)

    stats = {
        "status": "success",
        "total_words": len(all_words),
        "names_count": len(names),
        "places_count": len(places),
        "institutions_count": len(institutions),
        "field_patterns_count": len(field_patterns),
        "wordlist_path": str(wordlist_path),
        "config_path": str(config_path),
        "output_dir": str(tesseract_dir),
        "completed_at": datetime.now().isoformat(),
    }

    with open(tesseract_dir / "enhancement_stats.json", "w") as f:
        json.dump(stats, f, indent=2)

    print(f"  ✅ Tesseract enhancement complete!")
    print(f"     Words in dictionary: {len(all_words)}")
    print(f"     Names: {len(names)}, Places: {len(places)}")
    print(f"     Field patterns: {len(field_patterns)}")
    print(f"     Output: {tesseract_dir}")

    return stats


# ============================================================
# Stage 3: Ensemble Configuration
# ============================================================
def configure_ensemble(
    output_dir: Path,
    trocr_path: Optional[str] = None,
    tesseract_config_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Configure the ensemble OCR pipeline that combines TrOCR + Tesseract.
    """
    print("\n" + "=" * 70)
    print("  Stage 3: Ensemble OCR Configuration")
    print("=" * 70)

    ensemble_dir = output_dir / "ensemble"
    ensemble_dir.mkdir(parents=True, exist_ok=True)

    # Auto-detect model paths
    if not trocr_path:
        default_trocr = output_dir / "trocr_finetuned"
        if default_trocr.exists():
            trocr_path = str(default_trocr)

    if not tesseract_config_path:
        default_tesseract = output_dir / "tesseract_enhanced" / "admission_form.config"
        if default_tesseract.exists():
            tesseract_config_path = str(default_tesseract)

    # --- Build ensemble config ---
    config = {
        "ensemble_version": "1.0",
        "created_at": datetime.now().isoformat(),
        "providers": [
            {
                "name": "trocr_finetuned",
                "type": "trocr",
                "model_path": trocr_path or "microsoft/trocr-base-handwritten",
                "weight": 0.6,
                "is_finetuned": trocr_path is not None,
                "description": "Fine-tuned TrOCR for handwritten admission form text",
            },
            {
                "name": "tesseract_enhanced",
                "type": "tesseract",
                "config_path": tesseract_config_path,
                "wordlist_path": str(output_dir / "tesseract_enhanced" / "admission_forms.wordlist") if tesseract_config_path else None,
                "weight": 0.4,
                "is_enhanced": tesseract_config_path is not None,
                "description": "Tesseract with custom wordlists for admission forms",
            },
        ],
        "fusion_strategy": "weighted_confidence",
        "post_processing": {
            "field_mapper_enabled": True,
            "field_mapper_path": "backend/training/field_mapper.py",
            "validation_rules": {
                "aadhar_number": {"pattern": r"^\d{12}$", "type": "digits"},
                "pincode": {"pattern": r"^\d{6}$", "type": "digits"},
                "phone_number": {"pattern": r"^\d{10}$", "type": "digits"},
                "email": {"pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", "type": "email"},
                "date_of_birth": {"pattern": r"^\d{2}[/-]\d{2}[/-]\d{4}$", "type": "date"},
            },
        },
    }

    config_path = ensemble_dir / "ensemble_config.json"
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    print(f"  ✅ Ensemble configuration created!")
    print(f"     TrOCR model: {'fine-tuned' if trocr_path else 'base (not fine-tuned yet)'}")
    print(f"     Tesseract: {'enhanced' if tesseract_config_path else 'default'}")
    print(f"     Fusion: weighted_confidence (TrOCR={config['providers'][0]['weight']}, Tesseract={config['providers'][1]['weight']})")
    print(f"     Config: {config_path}")

    return {
        "status": "success",
        "config_path": str(config_path),
        "trocr_available": trocr_path is not None,
        "tesseract_enhanced": tesseract_config_path is not None,
    }


# ============================================================
# Main CLI
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description="Train OCR models for admission forms",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python train_ocr_pipeline.py                              # All stages
  python train_ocr_pipeline.py --stage 1                    # TrOCR only
  python train_ocr_pipeline.py --stage 2                    # Tesseract only
  python train_ocr_pipeline.py --epochs 1 --max-samples 5   # Quick test
  python train_ocr_pipeline.py --base-model microsoft/trocr-large-handwritten
        """
    )
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR), help="Training data directory")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_DIR), help="Output directory for models")
    parser.add_argument("--stage", type=int, choices=[1, 2, 3], help="Run specific stage only")
    parser.add_argument("--epochs", type=int, default=20, help="Training epochs (Stage 1)")
    parser.add_argument("--batch-size", type=int, default=8, help="Batch size (Stage 1)")
    parser.add_argument("--learning-rate", type=float, default=5e-5, help="Learning rate (Stage 1)")
    parser.add_argument("--base-model", default="microsoft/trocr-base-handwritten", help="Base TrOCR model")
    parser.add_argument("--max-samples", type=int, default=None, help="Limit training samples")

    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("  OCR Training Pipeline")
    print("=" * 70)
    print(f"  Data directory:   {data_dir}")
    print(f"  Output directory: {output_dir}")
    print(f"  Stages to run:    {'All' if not args.stage else f'Stage {args.stage}'}")
    print()

    results = {}
    start_time = time.time()

    # Stage 1: TrOCR Fine-Tuning
    if not args.stage or args.stage == 1:
        results["stage1_trocr"] = train_trocr(
            data_dir=data_dir,
            output_dir=output_dir,
            base_model=args.base_model,
            epochs=args.epochs,
            batch_size=args.batch_size,
            learning_rate=args.learning_rate,
            max_samples=args.max_samples,
        )

    # Stage 2: Tesseract Enhancement
    if not args.stage or args.stage == 2:
        results["stage2_tesseract"] = enhance_tesseract(
            data_dir=data_dir,
            output_dir=output_dir,
        )

    # Stage 3: Ensemble Configuration
    if not args.stage or args.stage == 3:
        trocr_path = None
        tesseract_config = None
        if "stage1_trocr" in results and results["stage1_trocr"].get("status") == "success":
            trocr_path = results["stage1_trocr"].get("model_path")
        if "stage2_tesseract" in results and results["stage2_tesseract"].get("status") == "success":
            tesseract_config = results["stage2_tesseract"].get("config_path")

        results["stage3_ensemble"] = configure_ensemble(
            output_dir=output_dir,
            trocr_path=trocr_path,
            tesseract_config_path=tesseract_config,
        )

    total_time = time.time() - start_time

    # --- Save overall results ---
    results["total_time_seconds"] = total_time
    results["completed_at"] = datetime.now().isoformat()

    with open(output_dir / "training_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

    print("\n" + "=" * 70)
    print("  🎉 Training Pipeline Complete!")
    print("=" * 70)
    print(f"  Total time: {total_time:.1f}s")
    for stage, result in results.items():
        if isinstance(result, dict) and "status" in result:
            status = "✅" if result["status"] == "success" else "⚠" if result["status"] == "skipped" else "✗"
            print(f"  {status} {stage}: {result['status']}")
    print(f"\n  Results saved to: {output_dir / 'training_results.json'}")


if __name__ == "__main__":
    main()
