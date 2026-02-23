"""
Multi-Engine OCR Comparison Test

Tests Tesseract, EasyOCR, and fine-tuned TrOCR on admission form images.
Compares outputs against verified ground-truth field values.
"""

import json
import time
import sys
from pathlib import Path
from difflib import SequenceMatcher

sys.path.insert(0, str(Path(__file__).parent))

PROJECT_ROOT = Path(__file__).parent


def fuzzy_find(value: str, text: str) -> float:
    """Find how well a field value matches within OCR text."""
    val = value.strip().lower()
    txt = text.lower()
    if val in txt:
        return 1.0
    words = txt.split()
    val_words = val.split()
    best = 0.0
    window = max(len(val_words), 1)
    for i in range(len(words) - window + 1):
        chunk = " ".join(words[i:i+window])
        ratio = SequenceMatcher(None, val, chunk).ratio()
        best = max(best, ratio)
    # Also try single-word matching for short values
    if len(val_words) == 1:
        for w in words:
            ratio = SequenceMatcher(None, val, w.lower()).ratio()
            best = max(best, ratio)
    return best


def test_tesseract(image_path: str) -> dict:
    """Run Tesseract OCR on an image."""
    try:
        import pytesseract
        from PIL import Image
        img = Image.open(image_path)
        start = time.time()
        text = pytesseract.image_to_string(img)
        elapsed = time.time() - start
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        confidences = [int(c) for c in data["conf"] if int(c) > 0]
        avg_conf = sum(confidences) / max(len(confidences), 1)
        return {"text": text, "confidence": avg_conf / 100.0, "time": elapsed, "engine": "Tesseract"}
    except Exception as e:
        return {"text": "", "confidence": 0, "time": 0, "engine": "Tesseract", "error": str(e)}


def test_easyocr(image_path: str, reader=None) -> dict:
    """Run EasyOCR on an image."""
    try:
        import easyocr
        if reader is None:
            reader = easyocr.Reader(["en"], gpu=False, verbose=False)
        start = time.time()
        results = reader.readtext(image_path)
        elapsed = time.time() - start
        text = " ".join([r[1] for r in results])
        confidences = [r[2] for r in results]
        avg_conf = sum(confidences) / max(len(confidences), 1)
        return {"text": text, "confidence": avg_conf, "time": elapsed, "engine": "EasyOCR", "_reader": reader}
    except Exception as e:
        return {"text": "", "confidence": 0, "time": 0, "engine": "EasyOCR", "error": str(e)}


def test_trocr_finetuned(image_path: str, processor=None, model=None) -> dict:
    """Run fine-tuned TrOCR on an image."""
    try:
        from PIL import Image
        from transformers import TrOCRProcessor, VisionEncoderDecoderModel

        model_path = str(PROJECT_ROOT / "training_output" / "models" / "trocr_finetuned")
        if processor is None:
            processor = TrOCRProcessor.from_pretrained(model_path)
            model = VisionEncoderDecoderModel.from_pretrained(model_path)

        img = Image.open(image_path).convert("RGB")
        start = time.time()
        pixel_values = processor(img, return_tensors="pt").pixel_values
        generated_ids = model.generate(pixel_values, max_new_tokens=200)
        text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
        elapsed = time.time() - start

        return {"text": text, "confidence": 0.5, "time": elapsed, "engine": "TrOCR-finetuned",
                "_processor": processor, "_model": model}
    except Exception as e:
        return {"text": "", "confidence": 0, "time": 0, "engine": "TrOCR-finetuned", "error": str(e)}


def test_trocr_base(image_path: str, processor=None, model=None) -> dict:
    """Run base (pretrained) TrOCR on an image for comparison."""
    try:
        from PIL import Image
        from transformers import TrOCRProcessor, VisionEncoderDecoderModel

        base_model = "microsoft/trocr-base-handwritten"
        if processor is None:
            processor = TrOCRProcessor.from_pretrained(base_model)
            model = VisionEncoderDecoderModel.from_pretrained(base_model)

        img = Image.open(image_path).convert("RGB")
        start = time.time()
        pixel_values = processor(img, return_tensors="pt").pixel_values
        generated_ids = model.generate(pixel_values, max_new_tokens=200)
        text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
        elapsed = time.time() - start

        return {"text": text, "confidence": 0.5, "time": elapsed, "engine": "TrOCR-base",
                "_processor": processor, "_model": model}
    except Exception as e:
        return {"text": "", "confidence": 0, "time": 0, "engine": "TrOCR-base", "error": str(e)}


def main():
    print("=" * 70)
    print("  Multi-Engine OCR Comparison Test")
    print("=" * 70)

    # Load ground truth
    training_data_path = PROJECT_ROOT / "training_data" / "prepared" / "training_data.json"
    with open(training_data_path, "r", encoding="utf-8") as f:
        all_records = json.load(f)

    # Find test records with images and fields
    test_records = [r for r in all_records
                    if r.get("split") == "test" and r.get("images") and r.get("fields")]
    if not test_records:
        test_records = [r for r in all_records if r.get("images") and r.get("fields")]

    # Use first 3 for speed
    test_records = test_records[:3]
    print(f"\n  Testing {len(test_records)} forms with ground-truth fields")

    # Initialize shared engines
    print("\n  Initializing engines...")
    easyocr_reader = None
    trocr_processor = trocr_model = None
    trocr_base_processor = trocr_base_model = None

    # Results storage
    engine_stats = {}

    for idx, rec in enumerate(test_records):
        if not rec["images"]:
            continue

        img_path = rec["images"][0]  # First page
        if not Path(img_path).exists():
            continue

        fields = rec.get("fields", {})
        non_empty_fields = {k: v for k, v in fields.items() if v and len(v.strip()) >= 2}

        print(f"\n{'─' * 70}")
        print(f"  Form {idx+1}: {Path(img_path).name}")
        print(f"  Ground-truth fields: {len(non_empty_fields)}")
        print(f"{'─' * 70}")

        # Show ground truth
        print("  Ground truth (first 5):")
        for i, (k, v) in enumerate(list(non_empty_fields.items())[:5]):
            print(f"    {k}: {v}")

        # Run each engine
        engines = [
            ("Tesseract", lambda p: test_tesseract(p)),
        ]

        # EasyOCR
        def run_easyocr(p):
            nonlocal easyocr_reader
            r = test_easyocr(p, easyocr_reader)
            easyocr_reader = r.pop("_reader", None)
            return r
        engines.append(("EasyOCR", run_easyocr))

        # Fine-tuned TrOCR
        def run_trocr_ft(p):
            nonlocal trocr_processor, trocr_model
            r = test_trocr_finetuned(p, trocr_processor, trocr_model)
            trocr_processor = r.pop("_processor", None)
            trocr_model = r.pop("_model", None)
            return r
        engines.append(("TrOCR-finetuned", run_trocr_ft))

        for engine_name, engine_func in engines:
            print(f"\n  ▶ {engine_name}...")
            result = engine_func(img_path)

            if result.get("error"):
                print(f"    ✗ Error: {result['error']}")
                continue

            text = result["text"]
            text_preview = text[:120].replace("\n", " ")
            print(f"    Time: {result['time']:.2f}s | Confidence: {result['confidence']:.2f}")
            print(f"    Text preview: {text_preview}...")

            # Score against ground truth
            matches = 0
            fuzzy_matches = 0
            for field_name, ground_truth in non_empty_fields.items():
                score = fuzzy_find(ground_truth, text)
                if score >= 0.95:
                    matches += 1
                if score >= 0.70:
                    fuzzy_matches += 1

            total = max(len(non_empty_fields), 1)
            print(f"    Exact matches: {matches}/{len(non_empty_fields)} ({matches/total:.0%})")
            print(f"    Fuzzy matches: {fuzzy_matches}/{len(non_empty_fields)} ({fuzzy_matches/total:.0%})")

            if engine_name not in engine_stats:
                engine_stats[engine_name] = {
                    "total_fields": 0, "exact": 0, "fuzzy": 0, "total_time": 0
                }
            engine_stats[engine_name]["total_fields"] += len(non_empty_fields)
            engine_stats[engine_name]["exact"] += matches
            engine_stats[engine_name]["fuzzy"] += fuzzy_matches
            engine_stats[engine_name]["total_time"] += result["time"]

    # Summary
    print(f"\n{'═' * 70}")
    print(f"  SUMMARY — Multi-Engine Comparison")
    print(f"{'═' * 70}")
    print(f"  {'Engine':<20} {'Exact%':>8} {'Fuzzy%':>8} {'Time(s)':>10}")
    print(f"  {'─'*20} {'─'*8} {'─'*8} {'─'*10}")

    for name, stats in engine_stats.items():
        total = max(stats["total_fields"], 1)
        print(f"  {name:<20} {stats['exact']/total:>7.0%} {stats['fuzzy']/total:>7.0%} {stats['total_time']:>9.1f}")

    # Save results
    results_path = PROJECT_ROOT / "training_output" / "multi_engine_comparison.json"
    results_path.parent.mkdir(parents=True, exist_ok=True)
    with open(results_path, "w") as f:
        json.dump(engine_stats, f, indent=2)
    print(f"\n  Results saved to: {results_path}")


if __name__ == "__main__":
    main()
