"""
OCR Model Evaluation Script

Benchmarks OCR models on admission forms by comparing OCR output
against verified ground-truth field values.

Metrics:
  - Character Error Rate (CER): Edit distance at character level
  - Word Error Rate (WER): Edit distance at word level
  - Per-field accuracy: Exact and fuzzy match rates
  - Overall accuracy score

Usage:
  python evaluate_ocr_models.py                              # Full evaluation
  python evaluate_ocr_models.py --max-forms 5                # Quick test
  python evaluate_ocr_models.py --provider tesseract          # Single provider
"""

import json
import os
import sys
import argparse
import asyncio
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from difflib import SequenceMatcher

sys.path.insert(0, str(Path(__file__).parent))

PROJECT_ROOT = Path(__file__).parent

# ============================================================
# Metrics
# ============================================================
def character_error_rate(reference: str, hypothesis: str) -> float:
    """Calculate Character Error Rate (CER) using Levenshtein distance."""
    if not reference:
        return 0.0 if not hypothesis else 1.0
    
    ref = reference.strip().lower()
    hyp = hypothesis.strip().lower()
    
    # Simple Levenshtein distance
    m, n = len(ref), len(hyp)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            cost = 0 if ref[i-1] == hyp[j-1] else 1
            dp[i][j] = min(dp[i-1][j] + 1, dp[i][j-1] + 1, dp[i-1][j-1] + cost)
    
    return dp[m][n] / max(m, 1)


def word_error_rate(reference: str, hypothesis: str) -> float:
    """Calculate Word Error Rate (WER)."""
    ref_words = reference.strip().lower().split()
    hyp_words = hypothesis.strip().lower().split()
    
    if not ref_words:
        return 0.0 if not hyp_words else 1.0
    
    m, n = len(ref_words), len(hyp_words)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            cost = 0 if ref_words[i-1] == hyp_words[j-1] else 1
            dp[i][j] = min(dp[i-1][j] + 1, dp[i][j-1] + 1, dp[i-1][j-1] + cost)
    
    return dp[m][n] / max(m, 1)


def fuzzy_match(reference: str, extracted: str, threshold: float = 0.8) -> Tuple[bool, float]:
    """Check if extracted value fuzzy-matches the reference."""
    ref = reference.strip().lower()
    ext = extracted.strip().lower()
    
    if ref == ext:
        return True, 1.0
    
    ratio = SequenceMatcher(None, ref, ext).ratio()
    return ratio >= threshold, ratio


def find_field_in_text(field_value: str, ocr_text: str) -> Tuple[bool, float]:
    """Check if a field value appears in OCR text (exact or fuzzy)."""
    val = field_value.strip().lower()
    text = ocr_text.lower()
    
    # Exact substring
    if val in text:
        return True, 1.0
    
    # Fuzzy match against text chunks
    words = text.split()
    val_words = val.split()
    best_ratio = 0.0
    
    if len(val_words) <= 3:
        # Short value: check individual words/groups
        for i in range(len(words)):
            for length in range(1, min(4, len(words) - i + 1)):
                chunk = " ".join(words[i:i+length])
                ratio = SequenceMatcher(None, val, chunk).ratio()
                best_ratio = max(best_ratio, ratio)
    else:
        # Long value: sliding window
        window = len(val_words)
        for i in range(len(words) - window + 1):
            chunk = " ".join(words[i:i+window])
            ratio = SequenceMatcher(None, val, chunk).ratio()
            best_ratio = max(best_ratio, ratio)
    
    return best_ratio >= 0.8, best_ratio


# ============================================================
# OCR Runner
# ============================================================
async def run_ocr_on_image(image, provider_name: str = "tesseract") -> Dict[str, Any]:
    """Run OCR on an image using specified provider."""
    try:
        from backend.ocr import get_ocr_provider
        provider = get_ocr_provider(provider_name)
        if not provider.is_available():
            return {"error": f"Provider {provider_name} not available"}
        result = await provider.extract_text(image)
        return result
    except Exception as e:
        return {"error": str(e)}


async def run_ocr_with_finetuned(image, model_path: str) -> Dict[str, Any]:
    """Run OCR with a fine-tuned TrOCR model."""
    try:
        from backend.ocr.craft_trocr_provider import CraftTrocrProvider
        provider = CraftTrocrProvider(custom_model_path=model_path)
        if not provider.is_available():
            return {"error": "Fine-tuned TrOCR not available"}
        result = await provider.extract_text(image)
        return result
    except Exception as e:
        return {"error": str(e)}


# ============================================================
# Evaluator
# ============================================================
async def evaluate_models(
    data_dir: Path,
    output_path: Path,
    providers: List[str],
    finetuned_model: Optional[str] = None,
    max_forms: Optional[int] = None,
) -> Dict[str, Any]:
    """Run evaluation across multiple OCR providers."""
    try:
        from PIL import Image
    except ImportError:
        print("  ✗ Pillow not installed")
        return {"error": "Pillow required"}

    # Load training data for ground truth
    training_data_path = data_dir / "training_data.json"
    if not training_data_path.exists():
        print("  ✗ Training data not found. Run prepare_all_training_data.py first.")
        return {"error": "Training data not found"}

    with open(training_data_path, "r", encoding="utf-8") as f:
        all_records = json.load(f)

    # Use test split for evaluation
    test_records = [r for r in all_records if r.get("split") == "test" and r.get("images")]
    if not test_records:
        # Fallback: use any records with images and fields
        test_records = [r for r in all_records if r.get("images") and r.get("fields")]

    if max_forms:
        test_records = test_records[:max_forms]

    print(f"  Evaluating on {len(test_records)} forms")
    print(f"  Providers: {', '.join(providers)}")
    if finetuned_model:
        print(f"  Fine-tuned model: {finetuned_model}")

    results = {
        "evaluation_date": datetime.now().isoformat(),
        "num_forms": len(test_records),
        "providers": {},
    }

    for provider_name in providers:
        print(f"\n  --- Evaluating: {provider_name} ---")
        provider_results = {
            "total_forms": 0,
            "total_fields": 0,
            "exact_matches": 0,
            "fuzzy_matches": 0,
            "cer_sum": 0.0,
            "wer_sum": 0.0,
            "field_results": {},
            "per_form": [],
        }

        for idx, rec in enumerate(test_records):
            if not rec.get("images") or not rec.get("fields"):
                continue

            # Use first page image
            img_path = rec["images"][0]
            if not Path(img_path).exists():
                continue

            provider_results["total_forms"] += 1
            image = Image.open(img_path).convert("RGB")

            # Run OCR
            if provider_name == "finetuned_trocr" and finetuned_model:
                ocr_result = await run_ocr_with_finetuned(image, finetuned_model)
            else:
                ocr_result = await run_ocr_on_image(image, provider_name)

            if "error" in ocr_result:
                print(f"    Form {idx+1}: ✗ {ocr_result['error']}")
                continue

            raw_text = ocr_result.get("raw_text", "")
            
            form_metrics = {
                "form_id": rec.get("id", f"form_{idx}"),
                "fields_evaluated": 0,
                "exact_matches": 0,
                "fuzzy_matches": 0,
            }

            # Compare each verified field against OCR output
            for field_name, ground_truth in rec["fields"].items():
                if not ground_truth or len(ground_truth.strip()) < 2:
                    continue

                provider_results["total_fields"] += 1
                form_metrics["fields_evaluated"] += 1

                found, similarity = find_field_in_text(ground_truth, raw_text)

                if field_name not in provider_results["field_results"]:
                    provider_results["field_results"][field_name] = {
                        "total": 0, "exact": 0, "fuzzy": 0, "avg_similarity": 0
                    }

                fr = provider_results["field_results"][field_name]
                fr["total"] += 1
                fr["avg_similarity"] = (fr["avg_similarity"] * (fr["total"] - 1) + similarity) / fr["total"]

                if similarity >= 0.95:
                    provider_results["exact_matches"] += 1
                    form_metrics["exact_matches"] += 1
                    fr["exact"] += 1
                if found:
                    provider_results["fuzzy_matches"] += 1
                    form_metrics["fuzzy_matches"] += 1
                    fr["fuzzy"] += 1

            # Calculate text-level CER/WER if ground truth text available
            if rec.get("raw_ocr_text"):
                cer = character_error_rate(rec["raw_ocr_text"], raw_text)
                wer = word_error_rate(rec["raw_ocr_text"], raw_text)
                provider_results["cer_sum"] += cer
                provider_results["wer_sum"] += wer
                form_metrics["cer"] = cer
                form_metrics["wer"] = wer

            provider_results["per_form"].append(form_metrics)
            status = "✓" if form_metrics["exact_matches"] > 0 else "○"
            print(f"    Form {idx+1}: {status} {form_metrics['exact_matches']}/{form_metrics['fields_evaluated']} exact matches")

        # Calculate aggregate metrics
        total = max(provider_results["total_fields"], 1)
        n_forms = max(provider_results["total_forms"], 1)
        provider_results["exact_match_rate"] = provider_results["exact_matches"] / total
        provider_results["fuzzy_match_rate"] = provider_results["fuzzy_matches"] / total
        provider_results["avg_cer"] = provider_results["cer_sum"] / n_forms
        provider_results["avg_wer"] = provider_results["wer_sum"] / n_forms

        results["providers"][provider_name] = provider_results

        print(f"\n  {provider_name} Summary:")
        print(f"    Exact match rate:  {provider_results['exact_match_rate']:.1%}")
        print(f"    Fuzzy match rate:  {provider_results['fuzzy_match_rate']:.1%}")
        print(f"    Avg CER: {provider_results['avg_cer']:.3f}")
        print(f"    Avg WER: {provider_results['avg_wer']:.3f}")

    # Save results
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    return results


# ============================================================
# Main CLI
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description="Evaluate OCR models on admission forms",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--data-dir", default=str(PROJECT_ROOT / "training_data" / "prepared"),
                        help="Directory with prepared training data")
    parser.add_argument("--output", default=str(PROJECT_ROOT / "training_output" / "evaluation_report.json"),
                        help="Output path for evaluation report")
    parser.add_argument("--provider", action="append", dest="providers",
                        help="OCR provider to evaluate (can specify multiple)")
    parser.add_argument("--finetuned-model", default=None,
                        help="Path to fine-tuned TrOCR model for evaluation")
    parser.add_argument("--max-forms", type=int, default=None,
                        help="Limit number of forms to evaluate")

    args = parser.parse_args()

    # Default providers
    if not args.providers:
        args.providers = ["tesseract"]
        # Auto-detect fine-tuned model
        finetuned_path = PROJECT_ROOT / "training_output" / "models" / "trocr_finetuned"
        if finetuned_path.exists():
            args.providers.append("finetuned_trocr")
            if not args.finetuned_model:
                args.finetuned_model = str(finetuned_path)

    print("=" * 70)
    print("  OCR Model Evaluation")
    print("=" * 70)
    print(f"  Data: {args.data_dir}")
    print(f"  Providers: {', '.join(args.providers)}")
    print()

    results = asyncio.run(evaluate_models(
        data_dir=Path(args.data_dir),
        output_path=Path(args.output),
        providers=args.providers,
        finetuned_model=args.finetuned_model,
        max_forms=args.max_forms,
    ))

    if "error" not in results:
        print(f"\n  📊 Report saved to: {args.output}")

        # Print comparison table
        if len(results.get("providers", {})) > 1:
            print("\n  ═══ Provider Comparison ═══")
            print(f"  {'Provider':<25} {'Exact%':>8} {'Fuzzy%':>8} {'CER':>8} {'WER':>8}")
            print(f"  {'─'*25} {'─'*8} {'─'*8} {'─'*8} {'─'*8}")
            for name, res in results["providers"].items():
                print(f"  {name:<25} {res['exact_match_rate']:>7.1%} {res['fuzzy_match_rate']:>7.1%} "
                      f"{res['avg_cer']:>7.3f} {res['avg_wer']:>7.3f}")


if __name__ == "__main__":
    main()
