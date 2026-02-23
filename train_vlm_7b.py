"""
Fine-Tune Qwen2.5-VL-7B on 53 Verified Admission Forms (210 Samples)

Uses LoRA (Low-Rank Adaptation) for memory-efficient training.
Trains on per-page (image, fields) pairs from verified admission forms.

Usage:
  python train_vlm_7b.py
  python train_vlm_7b.py --epochs 5
  python train_vlm_7b.py --eval-only --model-path training_output/vlm_7b_finetuned
"""

import json
import logging
import os
import sys
import time
import gc
from pathlib import Path
from typing import Dict, List, Any

import torch
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("training_log.txt", mode="w"),
    ]
)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent
MODEL_NAME = "Qwen/Qwen2.5-VL-7B-Instruct"
OUTPUT_DIR = PROJECT_ROOT / "training_output" / "vlm_7b_finetuned"


def get_page_prompt(page_number: int) -> str:
    """Get extraction prompt specific to each page of the SRCC admission form."""
    
    if page_number == 1:
        return """You are an expert document AI system. Extract ALL fields from this SRCC admission form (Page 1).

This page contains:
- Academic & Admission Details (top section)
- Personal Details (name, DOB, gender, etc.)
- Address Details (permanent and correspondence)
- Contact Details (phone, email)
- Parent Names (mother, father)
- CUET Marks Table (subjects, scores)

Return a JSON object with EXACTLY these field names and their values from the form:
{
  "academic_session": "",
  "course": "",
  "admission_category": "",
  "du_portal_form_number": "",
  "cuet_score": "",
  "college_roll_no": "",
  "date_of_admission": "",
  "first_name": "",
  "middle_name": "",
  "surname": "",
  "student_name": "",
  "gender": "",
  "date_of_birth": "",
  "category": "",
  "nationality": "",
  "religion": "",
  "aadhar_number": "",
  "blood_group": "",
  "below_poverty_line": "",
  "minority_category": "",
  "permanent_address_line1": "",
  "permanent_address_line2": "",
  "permanent_address_line3": "",
  "permanent_state": "",
  "permanent_pincode": "",
  "correspondence_address_line1": "",
  "correspondence_address_line2": "",
  "correspondence_address_line3": "",
  "correspondence_state": "",
  "correspondence_pincode": "",
  "phone_number": "",
  "alternate_phone": "",
  "email": "",
  "mother_name": "",
  "father_name": "",
  "cuet_subject_1": "", "cuet_total_score_1": "", "cuet_score_obtained_1": "",
  "cuet_subject_2": "", "cuet_total_score_2": "", "cuet_score_obtained_2": "",
  "cuet_subject_3": "", "cuet_total_score_3": "", "cuet_score_obtained_3": "",
  "cuet_subject_4": "", "cuet_total_score_4": "", "cuet_score_obtained_4": "",
  "cuet_subject_5": "", "cuet_total_score_5": "", "cuet_score_obtained_5": "",
  "cuet_subject_6": "", "cuet_total_score_6": "", "cuet_score_obtained_6": "",
  "cuet_total_score": ""
}

Rules:
- Use ALL CAPS for names
- Format dates as DD/MM/YYYY
- Write phone numbers as 10 digits only
- Leave empty string "" for fields not visible on this page
- Return ONLY the JSON object, nothing else"""

    elif page_number == 2:
        return """You are an expert document AI system. Extract ALL fields from this SRCC admission form (Page 2).

This page contains:
- Section 11: Qualifying Examination Details
- Section 12: Personal Information (income, etc.)
- Section 13: Mother's Occupational Details
- Section 14: Father's Occupational Details
- Section 15: Local Guardian's Details
- Section 16: Other Information
- Section 17: EWS/SC/ST/OBC/PwBD Details

Return a JSON object with EXACTLY these field names:
{
  "twelfth_year": "",
  "twelfth_board": "",
  "twelfth_roll_number": "",
  "twelfth_institution": "",
  "hindi_studied_upto": "",
  "annual_income": "",
  "mother_occupation": "",
  "mother_designation": "",
  "mother_organization": "",
  "mother_email": "",
  "mother_mobile": "",
  "father_occupation": "",
  "father_designation": "",
  "father_organization": "",
  "father_email": "",
  "father_mobile": "",
  "guardian_name": "",
  "guardian_residential_address": "",
  "guardian_email": "",
  "guardian_mobile": "",
  "guardian_relation": "",
  "du_enrollment_number": "",
  "hindi_medium_preference": "",
  "category_certificate_authority": "",
  "category_certificate_number": "",
  "category_certificate_date": "",
  "disability_percentage": "",
  "disability_type": "",
  "udid_number": ""
}

Rules:
- Use ALL CAPS for names and institutions
- Phone numbers: 10 digits only
- Leave empty "" for unfilled fields
- Return ONLY the JSON object"""

    elif page_number == 4:
        return """You are an expert document AI system. Extract the document checklist from this SRCC admission form (Page 4).

This page contains a checklist of submitted documents. For each document, indicate "Yes" if the checkbox is ticked/checked, "No" if unchecked.

Return a JSON object:
{
  "doc_admission_form": "",
  "doc_undertaking_ragging": "",
  "doc_photographs": "",
  "doc_cuet_scorecard": "",
  "doc_class_xii_marksheet": "",
  "doc_class_x_certificate": "",
  "doc_class_xii_certificate": "",
  "doc_character_certificate": "",
  "doc_transfer_certificate": "",
  "doc_hindi_certificate": "",
  "doc_caste_certificate": "",
  "doc_sports_eca": "",
  "doc_originals": "",
  "doc_photo_id": ""
}

Return ONLY the JSON object."""

    else:
        return """You are an expert document AI system. Extract any visible form fields from this admission form page.
Return a JSON object mapping field names to their values. Use ALL CAPS for names.
Return ONLY the JSON object."""


def load_training_data():
    """Load the prepared training manifest with 210 samples."""
    manifest_path = PROJECT_ROOT / "training_data" / "vlm_training" / "training_manifest.json"
    
    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    samples = data["samples"]
    logger.info(f"Loaded {len(samples)} training samples from {data['total_forms']} forms")
    
    # Validate: check images exist
    valid = []
    for s in samples:
        if os.path.exists(s["image_path"]) and len(s["fields"]) >= 3:
            valid.append(s)
    
    logger.info(f"Valid samples (image exists + 3+ fields): {len(valid)}")
    return valid


def train_with_lora(samples: List[Dict],
                    model_name: str = MODEL_NAME,
                    output_dir: str = None,
                    epochs: int = 3,
                    lr: float = 1e-5,
                    gradient_accumulation: int = 4):
    """
    Fine-tune Qwen2.5-VL-7B with LoRA on admission form data.
    
    Key optimizations for CPU training:
    - LoRA rank 8 (less memory than rank 16)
    - Gradient accumulation (simulates larger batch without memory cost)
    - Mixed precision where possible
    - Gradient checkpointing
    """
    from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor
    from qwen_vl_utils import process_vision_info
    
    if output_dir is None:
        output_dir = str(OUTPUT_DIR)
    os.makedirs(output_dir, exist_ok=True)
    
    # Device setup
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32
    
    logger.info("=" * 70)
    logger.info("  QWEN2.5-VL-7B FINE-TUNING WITH LoRA")
    logger.info("=" * 70)
    logger.info(f"  Model: {model_name}")
    logger.info(f"  Training samples: {len(samples)}")
    logger.info(f"  Epochs: {epochs}")
    logger.info(f"  Learning rate: {lr}")
    logger.info(f"  Gradient accumulation: {gradient_accumulation}")
    logger.info(f"  Device: {device} | Dtype: {dtype}")
    logger.info(f"  Output: {output_dir}")
    logger.info("=" * 70)
    
    # Load model
    logger.info("Loading Qwen2.5-VL-7B-Instruct (this downloads ~15GB on first run)...")
    model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
        model_name,
        torch_dtype=dtype,
        device_map="auto" if device == "cuda" else None,
        low_cpu_mem_usage=True,
    )
    
    processor = AutoProcessor.from_pretrained(
        model_name,
        min_pixels=256 * 28 * 28,
        max_pixels=1024 * 28 * 28,  # Slightly smaller for 7B memory
    )
    
    # Apply LoRA
    try:
        from peft import LoraConfig, get_peft_model, TaskType
        
        lora_config = LoraConfig(
            task_type=TaskType.CAUSAL_LM,
            r=8,                     # Rank 8 — good balance for 7B
            lora_alpha=16,           # Alpha = 2*r
            lora_dropout=0.05,
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                           "gate_proj", "up_proj", "down_proj"],
            bias="none",
        )
        
        model = get_peft_model(model, lora_config)
        trainable, total = model.get_nb_trainable_parameters()
        logger.info(f"LoRA applied: {trainable:,} trainable / {total:,} total ({trainable/total*100:.2f}%)")
        
    except ImportError:
        logger.warning("PEFT not installed — training full model (requires much more memory)")
    
    # Enable gradient checkpointing to save memory
    model.gradient_checkpointing_enable()
    
    if device == "cpu":
        model = model.to(dtype=torch.float32)
    
    # Optimizer
    from torch.optim import AdamW
    optimizer = AdamW(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=lr,
        weight_decay=0.01,
        betas=(0.9, 0.95),
    )
    
    model.train()
    loss_history = []
    best_loss = float('inf')
    
    total_steps = len(samples) * epochs
    step = 0
    
    for epoch in range(epochs):
        epoch_loss = 0
        epoch_samples = 0
        epoch_start = time.time()
        
        # Shuffle samples each epoch
        import random
        random.shuffle(samples)
        
        optimizer.zero_grad()
        
        for i, sample in enumerate(samples):
            step += 1
            
            try:
                # Load image
                img = Image.open(sample["image_path"]).convert("RGB")
                
                # Resize for memory efficiency
                w, h = img.size
                max_dim = 800  # Smaller for 7B training
                if max(w, h) > max_dim:
                    ratio = max_dim / max(w, h)
                    img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
                
                # Get page-specific prompt
                page_num = sample.get("page_number", 1)
                prompt = get_page_prompt(page_num)
                
                # Target JSON
                target = json.dumps(sample["fields"], ensure_ascii=False, indent=2)
                
                # Build conversation
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {"type": "image", "image": img},
                            {"type": "text", "text": prompt},
                        ],
                    },
                    {
                        "role": "assistant",
                        "content": [
                            {"type": "text", "text": target},
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
                
                inputs["labels"] = inputs["input_ids"].clone()
                
                # Forward pass
                outputs = model(**inputs)
                loss = outputs.loss / gradient_accumulation
                
                # Backward
                loss.backward()
                
                epoch_loss += loss.item() * gradient_accumulation
                epoch_samples += 1
                
                # Gradient accumulation step
                if (i + 1) % gradient_accumulation == 0 or (i + 1) == len(samples):
                    torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                    optimizer.step()
                    optimizer.zero_grad()
                
                # Logging
                if (i + 1) % 10 == 0 or (i + 1) == len(samples):
                    avg = epoch_loss / epoch_samples
                    elapsed = time.time() - epoch_start
                    eta = elapsed / epoch_samples * (len(samples) - epoch_samples)
                    logger.info(
                        f"  Epoch {epoch+1}/{epochs} | "
                        f"Step {i+1}/{len(samples)} | "
                        f"Loss: {avg:.4f} | "
                        f"ETA: {eta/60:.0f}min"
                    )
                
                # Free memory
                del inputs, outputs, loss
                gc.collect()
                if device == "cuda":
                    torch.cuda.empty_cache()
                    
            except Exception as e:
                logger.error(f"  Error on sample {i} ({sample.get('filename')}): {e}")
                optimizer.zero_grad()
                gc.collect()
                continue
        
        avg_loss = epoch_loss / max(epoch_samples, 1)
        epoch_time = time.time() - epoch_start
        loss_history.append(avg_loss)
        
        logger.info(f"\n  ═══ Epoch {epoch+1} Complete ═══")
        logger.info(f"  Avg Loss: {avg_loss:.4f}")
        logger.info(f"  Time: {epoch_time/60:.1f} min")
        logger.info(f"  Samples processed: {epoch_samples}/{len(samples)}")
        
        # Save best model
        if avg_loss < best_loss:
            best_loss = avg_loss
            logger.info(f"  New best model! Saving checkpoint...")
            model.save_pretrained(output_dir)
            processor.save_pretrained(output_dir)
    
    # Final save
    logger.info("\nSaving final model...")
    model.save_pretrained(output_dir)
    processor.save_pretrained(output_dir)
    
    # Save results
    results = {
        "model": model_name,
        "epochs": epochs,
        "learning_rate": lr,
        "total_samples": len(samples),
        "gradient_accumulation": gradient_accumulation,
        "loss_history": loss_history,
        "final_loss": loss_history[-1] if loss_history else None,
        "best_loss": best_loss,
        "output_dir": output_dir,
        "device": device,
    }
    
    with open(os.path.join(output_dir, "training_results.json"), "w") as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"\n{'='*70}")
    logger.info(f"  ✅ TRAINING COMPLETE")
    logger.info(f"  Model saved: {output_dir}")
    logger.info(f"  Loss: {' → '.join(f'{l:.4f}' for l in loss_history)}")
    logger.info(f"  Best loss: {best_loss:.4f}")
    logger.info(f"{'='*70}")
    
    return results


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Fine-tune Qwen2.5-VL-7B for Admission Forms")
    parser.add_argument("--model", default=MODEL_NAME)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--lr", type=float, default=1e-5)
    parser.add_argument("--grad-accum", type=int, default=4)
    parser.add_argument("--eval-only", action="store_true")
    parser.add_argument("--model-path", help="Path to fine-tuned model")
    args = parser.parse_args()
    
    # Load training data
    logger.info("Loading training data...")
    samples = load_training_data()
    
    if not samples:
        logger.error("No training data found! Run prepare_vlm_training.py first.")
        return
    
    # Train
    results = train_with_lora(
        samples,
        model_name=args.model,
        epochs=args.epochs,
        lr=args.lr,
        gradient_accumulation=args.grad_accum,
    )
    
    logger.info("\n✅ Done! Fine-tuned model ready for inference.")


if __name__ == "__main__":
    main()
