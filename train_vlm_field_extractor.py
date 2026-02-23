"""
Fine-Tuning Script for Qwen2.5-VL on Admission Forms

Uses LoRA (Low-Rank Adaptation) to fine-tune Qwen2.5-VL-3B on
verified admission form data for superior field extraction accuracy.

This is how Azure/Google train their Document AI models — supervised 
fine-tuning on labeled document-field pairs.

Usage:
  python train_vlm_field_extractor.py
  python train_vlm_field_extractor.py --model Qwen/Qwen2.5-VL-7B-Instruct
  python train_vlm_field_extractor.py --epochs 5 --lr 2e-5
"""

import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Any

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent
TRAINING_OUTPUT = PROJECT_ROOT / "training_output" / "vlm_finetuned"


def load_training_data() -> List[Dict[str, Any]]:
    """
    Load training data: image paths + verified field JSON pairs.
    
    Sources:
      1. verified_samples.json — human-verified field values
      2. prepared training_data.json — images with fields
    """
    samples = []
    
    # Source 1: Verified samples with extracted_fields
    verified_path = PROJECT_ROOT / "training_data" / "google_ocr" / "verified_samples.json"
    if verified_path.exists():
        with open(verified_path, "r", encoding="utf-8") as f:
            verified = json.load(f)
        logger.info(f"  Loaded {len(verified)} verified samples")
        
        for v in verified:
            fields = v.get("extracted_fields", {})
            # We need images for these — check prepared data
            samples.append({
                "form_id": v.get("form_id"),
                "fields": fields,
                "source": "verified",
            })
    
    # Source 2: Prepared training data with images
    prepared_path = PROJECT_ROOT / "training_data" / "prepared" / "training_data.json"
    if prepared_path.exists():
        with open(prepared_path, "r", encoding="utf-8") as f:
            prepared = json.load(f)
        
        for rec in prepared:
            images = rec.get("images", [])
            fields = rec.get("fields", {})
            existing_imgs = [p for p in images if Path(p).exists()]
            
            if existing_imgs and fields and len([v for v in fields.values() if v]) >= 5:
                samples.append({
                    "images": existing_imgs,
                    "fields": fields,
                    "source": "prepared",
                })
        
        logger.info(f"  Loaded {len([s for s in samples if s.get('images')])} samples with images")
    
    return samples


def create_training_dataset(samples: List[Dict], model_name: str):
    """
    Create a HuggingFace Dataset for VLM fine-tuning.
    
    Each sample: (image, instruction, target_json)
    """
    from backend.ocr.vlm_field_extractor import get_extraction_prompt
    
    dataset_items = []
    prompt = get_extraction_prompt()
    
    for sample in samples:
        images = sample.get("images", [])
        if not images:
            continue
        
        fields = sample.get("fields", {})
        # Clean: only non-empty fields
        clean_fields = {k: str(v) for k, v in fields.items() if v and str(v).strip()}
        
        if len(clean_fields) < 3:
            continue
        
        # Use first page image
        img_path = images[0]
        if not Path(img_path).exists():
            continue
        
        target_json = json.dumps(clean_fields, ensure_ascii=False, indent=2)
        
        dataset_items.append({
            "image_path": img_path,
            "instruction": prompt,
            "target": target_json,
            "fields": clean_fields,
        })
    
    logger.info(f"  Created {len(dataset_items)} training samples")
    return dataset_items


def train_with_lora(dataset_items: List[Dict], 
                    model_name: str = "Qwen/Qwen2.5-VL-3B-Instruct",
                    output_dir: str = None,
                    epochs: int = 3,
                    lr: float = 2e-5,
                    batch_size: int = 1):
    """
    Fine-tune Qwen2.5-VL with LoRA on admission form data.
    
    Uses Parameter-Efficient Fine-Tuning (PEFT) for low memory usage.
    """
    import torch
    from transformers import (
        Qwen2_5_VLForConditionalGeneration, 
        AutoProcessor,
        TrainingArguments,
    )
    
    if output_dir is None:
        output_dir = str(TRAINING_OUTPUT)
    
    os.makedirs(output_dir, exist_ok=True)
    
    logger.info(f"=" * 60)
    logger.info(f"  VLM Fine-Tuning with LoRA")
    logger.info(f"  Model: {model_name}")
    logger.info(f"  Samples: {len(dataset_items)}")
    logger.info(f"  Epochs: {epochs}")
    logger.info(f"  Learning Rate: {lr}")
    logger.info(f"=" * 60)
    
    # Detect device
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    logger.info(f"  Device: {device} | Dtype: {dtype}")
    
    # Load model
    logger.info("  Loading model...")
    model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
        model_name,
        torch_dtype=dtype,
        device_map=device if device == "cuda" else None,
    )
    
    processor = AutoProcessor.from_pretrained(
        model_name,
        min_pixels=256*28*28,
        max_pixels=1280*28*28,
    )
    
    # Apply LoRA
    try:
        from peft import LoraConfig, get_peft_model, TaskType
        
        lora_config = LoraConfig(
            task_type=TaskType.CAUSAL_LM,
            r=16,                    # LoRA rank
            lora_alpha=32,           # LoRA scaling
            lora_dropout=0.05,
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                           "gate_proj", "up_proj", "down_proj"],
            bias="none",
        )
        
        model = get_peft_model(model, lora_config)
        trainable_params, total_params = model.get_nb_trainable_parameters()
        logger.info(f"  LoRA applied: {trainable_params:,} trainable / {total_params:,} total params")
        logger.info(f"  Trainable: {trainable_params/total_params*100:.2f}%")
        
    except ImportError:
        logger.warning("  PEFT not available — training full model (requires more memory)")
    
    if device == "cpu":
        model = model.to(dtype=torch.float32)
    
    # Training loop (manual since HF Trainer doesn't natively handle VLM images well)
    from torch.optim import AdamW
    from qwen_vl_utils import process_vision_info
    
    optimizer = AdamW(model.parameters(), lr=lr, weight_decay=0.01)
    model.train()
    
    loss_history = []
    
    for epoch in range(epochs):
        epoch_loss = 0
        epoch_start = time.time()
        
        for i, item in enumerate(dataset_items):
            try:
                # Build conversation
                img = Image.open(item["image_path"]).convert("RGB")
                
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {"type": "image", "image": img},
                            {"type": "text", "text": item["instruction"]},
                        ],
                    },
                    {
                        "role": "assistant",
                        "content": [
                            {"type": "text", "text": item["target"]},
                        ],
                    }
                ]
                
                # Process inputs
                text = processor.apply_chat_template(
                    messages, tokenize=False, add_generation_prompt=False
                )
                image_inputs, video_inputs = process_vision_info(messages)
                inputs = processor(
                    text=[text],
                    images=image_inputs,
                    videos=video_inputs,
                    padding=True,
                    return_tensors="pt",
                )
                
                if device == "cuda":
                    inputs = inputs.to("cuda")
                
                # Labels = input_ids (causal LM)
                inputs["labels"] = inputs["input_ids"].clone()
                
                # Forward pass
                outputs = model(**inputs)
                loss = outputs.loss
                
                # Backward
                loss.backward()
                optimizer.step()
                optimizer.zero_grad()
                
                epoch_loss += loss.item()
                
                if (i + 1) % 5 == 0:
                    avg = epoch_loss / (i + 1)
                    logger.info(f"  Epoch {epoch+1}/{epochs} | Step {i+1}/{len(dataset_items)} | Loss: {avg:.4f}")
                    
            except Exception as e:
                logger.error(f"  Error on sample {i}: {e}")
                continue
        
        avg_loss = epoch_loss / max(len(dataset_items), 1)
        epoch_time = time.time() - epoch_start
        loss_history.append(avg_loss)
        logger.info(f"  Epoch {epoch+1} complete | Avg Loss: {avg_loss:.4f} | Time: {epoch_time:.0f}s")
    
    # Save model
    logger.info("  Saving fine-tuned model...")
    model.save_pretrained(output_dir)
    processor.save_pretrained(output_dir)
    
    # Save training results
    results = {
        "model": model_name,
        "epochs": epochs,
        "learning_rate": lr,
        "samples": len(dataset_items),
        "loss_history": loss_history,
        "final_loss": loss_history[-1] if loss_history else None,
        "output_dir": output_dir,
        "device": device,
    }
    
    results_path = Path(output_dir) / "training_results.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"  ✅ Model saved to: {output_dir}")
    logger.info(f"  📊 Loss: {' → '.join(f'{l:.4f}' for l in loss_history)}")
    
    return results


def evaluate_model(model_path: str, test_samples: List[Dict] = None):
    """Evaluate fine-tuned model against test data."""
    from difflib import SequenceMatcher
    from backend.ocr.vlm_field_extractor import VLMFieldExtractor
    
    logger.info(f"\n{'=' * 60}")
    logger.info(f"  Evaluating: {model_path}")
    logger.info(f"{'=' * 60}")
    
    extractor = VLMFieldExtractor(custom_model_path=model_path)
    
    if test_samples is None:
        # Use verified samples as test
        verified_path = PROJECT_ROOT / "training_data" / "google_ocr" / "verified_samples.json"
        with open(verified_path, "r", encoding="utf-8") as f:
            verified = json.load(f)
        
        # Find corresponding images
        prepared_path = PROJECT_ROOT / "training_data" / "prepared" / "training_data.json"
        with open(prepared_path, "r", encoding="utf-8") as f:
            prepared = json.load(f)
        
        test_samples = []
        for rec in prepared[:5]:
            images = [p for p in rec.get("images", []) if Path(p).exists()]
            fields = rec.get("fields", {})
            if images and fields:
                test_samples.append({"images": images, "fields": fields})
    
    exact_total = fuzzy_total = total_fields = 0
    
    for i, sample in enumerate(test_samples[:3]):
        img_path = sample["images"][0]
        gt_fields = {k: v for k, v in sample["fields"].items() 
                     if v and len(str(v).strip()) >= 2 and not k.startswith("doc_")}
        
        logger.info(f"\n  Test {i+1}: {Path(img_path).name} ({len(gt_fields)} fields)")
        
        img = Image.open(img_path).convert("RGB")
        pred_fields = extractor.extract_fields_from_image(img)
        
        # Score
        for key, gt_val in gt_fields.items():
            total_fields += 1
            pred_val = pred_fields.get(key, "")
            
            if not pred_val:
                continue
            
            ratio = SequenceMatcher(None, 
                                     str(gt_val).lower().strip(), 
                                     str(pred_val).lower().strip()).ratio()
            if ratio >= 0.95:
                exact_total += 1
            if ratio >= 0.70:
                fuzzy_total += 1
    
    logger.info(f"\n  Results:")
    logger.info(f"    Exact Match: {exact_total}/{total_fields} ({exact_total/max(total_fields,1)*100:.1f}%)")
    logger.info(f"    Fuzzy Match: {fuzzy_total}/{total_fields} ({fuzzy_total/max(total_fields,1)*100:.1f}%)")
    
    return {
        "exact_rate": round(exact_total / max(total_fields, 1), 3),
        "fuzzy_rate": round(fuzzy_total / max(total_fields, 1), 3),
        "total_fields": total_fields,
    }


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Fine-tune VLM for Admission Forms")
    parser.add_argument("--model", default="Qwen/Qwen2.5-VL-3B-Instruct")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--lr", type=float, default=2e-5)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--eval-only", action="store_true",
                       help="Only evaluate existing model")
    parser.add_argument("--model-path", help="Path to fine-tuned model for evaluation")
    args = parser.parse_args()
    
    if args.eval_only and args.model_path:
        evaluate_model(args.model_path)
        return
    
    # Load data
    logger.info("Loading training data...")
    samples = load_training_data()
    
    # Create dataset
    logger.info("Creating training dataset...")
    dataset_items = create_training_dataset(samples, args.model)
    
    if not dataset_items:
        logger.error("No training samples found! Check training_data/ directory.")
        return
    
    # Train
    results = train_with_lora(
        dataset_items,
        model_name=args.model,
        epochs=args.epochs,
        lr=args.lr,
        batch_size=args.batch_size,
    )
    
    # Evaluate
    logger.info("\nEvaluating fine-tuned model...")
    eval_results = evaluate_model(results["output_dir"])
    
    logger.info(f"\n{'=' * 60}")
    logger.info(f"  TRAINING COMPLETE")
    logger.info(f"  Model: {results['output_dir']}")
    logger.info(f"  Final Loss: {results['final_loss']:.4f}")
    logger.info(f"  Accuracy: {eval_results['exact_rate']*100:.1f}% exact / {eval_results['fuzzy_rate']*100:.1f}% fuzzy")
    logger.info(f"{'=' * 60}")


if __name__ == "__main__":
    main()
