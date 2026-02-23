"""
Test Script — Smart Document AI on Real Admission Forms

Downloads Qwen2.5-VL-3B and tests field extraction on actual form images.
This is the moment of truth — can open-source VLMs match Google Vision AI?
"""

import json
import os
import sys
import time
from pathlib import Path
from difflib import SequenceMatcher

os.environ["PATH"] = r"C:\Program Files\Tesseract-OCR" + os.pathsep + os.environ.get("PATH", "")
sys.path.insert(0, str(Path(__file__).parent))

PROJECT_ROOT = Path(__file__).parent


def fuzzy_score(value, predicted):
    """Score prediction against ground truth (0-1)."""
    if not value or not predicted:
        return 0.0
    return SequenceMatcher(None, str(value).lower().strip(), str(predicted).lower().strip()).ratio()


def main():
    print("=" * 70)
    print("  🧠 Smart Document AI — World-Class Form Extraction Test")
    print("  Using: Qwen2.5-VL-3B-Instruct (Vision-Language Model)")
    print("=" * 70)
    
    # Load test data
    prepared_path = PROJECT_ROOT / "training_data" / "prepared" / "training_data.json"
    with open(prepared_path, "r", encoding="utf-8") as f:
        prepared = json.load(f)
    
    # Find forms with images AND fields (for accuracy testing)
    test_forms = []
    for rec in prepared:
        images = [p for p in rec.get("images", []) if Path(p).exists()]
        fields = {k: v for k, v in rec.get("fields", {}).items()
                  if v and len(str(v).strip()) >= 2 and not k.startswith("doc_")}
        if images and len(fields) >= 5:
            test_forms.append({"images": images, "fields": fields})
    
    print(f"\n  Found {len(test_forms)} test forms with images + ground truth")
    
    # Use first 3 for testing
    test_set = test_forms[:3]
    
    # Initialize VLM extractor
    print("\n  Loading Qwen2.5-VL-3B-Instruct...")
    print("  (First run downloads ~6GB model from HuggingFace)")
    
    from backend.ocr.vlm_field_extractor import VLMFieldExtractor
    
    extractor = VLMFieldExtractor(
        model_name="Qwen/Qwen2.5-VL-3B-Instruct",
        use_quantization=False,  # Use full precision on CPU
    )
    
    # Load model
    start = time.time()
    extractor.load_model()
    load_time = time.time() - start
    print(f"  ✅ Model loaded in {load_time:.1f}s")
    
    # Test each form
    all_exact = all_fuzzy = all_total = 0
    all_times = []
    
    for form_idx, form in enumerate(test_set):
        img_path = form["images"][0]  # Single page for now
        gt_fields = form["fields"]
        
        img_name = Path(img_path).name
        print(f"\n{'━' * 70}")
        print(f"  Form {form_idx+1}: {img_name} ({len(gt_fields)} ground-truth fields)")
        print(f"{'━' * 70}")
        
        # Extract with VLM
        from PIL import Image
        img = Image.open(img_path).convert("RGB")
        
        start = time.time()
        pred_fields = extractor.extract_fields_from_image(img, "Page 1 — student details, CUET marks")
        extract_time = time.time() - start
        all_times.append(extract_time)
        
        predicted_count = len([v for v in pred_fields.values() if v and v.strip()])
        print(f"  ⏱  Extraction time: {extract_time:.1f}s")
        print(f"  📋 Fields predicted: {predicted_count}")
        
        # Score against ground truth
        form_exact = form_fuzzy = form_total = 0
        
        print(f"\n  {'Field':<35} {'Ground Truth':<25} {'Predicted':<25} {'Score':>6}")
        print(f"  {'─' * 35} {'─' * 25} {'─' * 25} {'─' * 6}")
        
        for key, gt_val in sorted(gt_fields.items()):
            form_total += 1
            pred_val = pred_fields.get(key, "")
            score = fuzzy_score(gt_val, pred_val)
            
            if score >= 0.95:
                form_exact += 1
                marker = "✅"
            elif score >= 0.70:
                marker = "🟡"
            else:
                marker = "❌"
            
            if score >= 0.70:
                form_fuzzy += 1
            
            # Truncate for display
            gt_display = str(gt_val)[:23]
            pred_display = str(pred_val)[:23] if pred_val else "(empty)"
            print(f"  {key:<35} {gt_display:<25} {pred_display:<25} {score:>5.0%} {marker}")
        
        e_pct = form_exact / max(form_total, 1) * 100
        f_pct = form_fuzzy / max(form_total, 1) * 100
        print(f"\n  📊 Form {form_idx+1} Results: Exact {form_exact}/{form_total} ({e_pct:.0f}%) | Fuzzy {form_fuzzy}/{form_total} ({f_pct:.0f}%)")
        
        all_exact += form_exact
        all_fuzzy += form_fuzzy
        all_total += form_total
    
    # Final summary
    print(f"\n{'═' * 70}")
    print(f"  ⭐ SMART DOCUMENT AI — FINAL RESULTS")
    print(f"{'═' * 70}")
    
    t = max(all_total, 1)
    avg_time = sum(all_times) / max(len(all_times), 1)
    
    print(f"\n  Qwen2.5-VL-3B (single page):")
    print(f"    Exact Match:  {all_exact}/{all_total} ({all_exact/t*100:.1f}%)")
    print(f"    Fuzzy Match:  {all_fuzzy}/{all_total} ({all_fuzzy/t*100:.1f}%)")
    print(f"    Avg Time:     {avg_time:.1f}s per page")
    
    print(f"\n  Comparison (from previous tests):")
    print(f"    Google Vision AI:  88.9% exact / 96.7% fuzzy  (cloud, multi-page)")
    print(f"    Tesseract:         15.0% exact / 23.0% fuzzy  (local, single-page)")
    print(f"    EasyOCR:           15.0% exact / 30.0% fuzzy  (local, single-page)")
    
    gap = 88.9 - all_exact/t*100
    if gap <= 5:
        print(f"\n  🏆 WITHIN 5% OF GOOGLE VISION AI! Outstanding!")
    elif gap <= 15:
        print(f"\n  🎯 Good results! {gap:.1f}% gap to Google Vision (multi-page vs single-page)")
    else:
        print(f"\n  ⚠ {gap:.1f}% gap — fine-tuning with LoRA should close this")
    
    # Save results
    results = {
        "model": "Qwen/Qwen2.5-VL-3B-Instruct",
        "test_forms": len(test_set),
        "exact_match_rate": round(all_exact / t, 3),
        "fuzzy_match_rate": round(all_fuzzy / t, 3),
        "total_fields": all_total,
        "avg_time_seconds": round(avg_time, 1),
    }
    
    out_path = PROJECT_ROOT / "training_output" / "smart_document_ai_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n  📊 Results saved to: {out_path}")


if __name__ == "__main__":
    main()
