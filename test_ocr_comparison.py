"""Quick Tesseract + EasyOCR comparison on a test form."""
import json
import time
import os
import sys
from pathlib import Path
from difflib import SequenceMatcher

sys.path.insert(0, str(Path(__file__).parent))

# Set Tesseract path
os.environ["PATH"] = r"C:\Program Files\Tesseract-OCR" + os.pathsep + os.environ.get("PATH", "")

PROJECT_ROOT = Path(__file__).parent


def fuzzy_find(value, text):
    val = value.strip().lower()
    txt = text.lower()
    if val in txt:
        return 1.0
    words = txt.split()
    val_words = val.split()
    best = 0.0
    window = max(len(val_words), 1)
    for i in range(max(len(words) - window + 1, 0)):
        chunk = " ".join(words[i:i+window])
        ratio = SequenceMatcher(None, val, chunk).ratio()
        best = max(best, ratio)
    if len(val_words) == 1:
        for w in words:
            ratio = SequenceMatcher(None, val, w.lower()).ratio()
            best = max(best, ratio)
    return best


def evaluate_engine(engine_name, ocr_func, image_path, fields):
    print(f"\n  [{engine_name}]")
    start = time.time()
    try:
        text, conf = ocr_func(image_path)
    except Exception as e:
        print(f"    ERROR: {e}")
        return None

    elapsed = time.time() - start
    print(f"    Time: {elapsed:.1f}s | Confidence: {conf:.2f}")
    print(f"    Text length: {len(text)} chars")
    print(f"    Preview: {text[:150].replace(chr(10), ' ')}...")

    exact = fuzzy70 = 0
    for k, v in fields.items():
        score = fuzzy_find(v, text)
        if score >= 0.95:
            exact += 1
        if score >= 0.70:
            fuzzy70 += 1

    total = max(len(fields), 1)
    print(f"    Exact match:  {exact}/{len(fields)} ({exact/total:.0%})")
    print(f"    Fuzzy (>=70%): {fuzzy70}/{len(fields)} ({fuzzy70/total:.0%})")
    return {"exact": exact, "fuzzy": fuzzy70, "total": len(fields), "time": elapsed, "conf": conf, "text_len": len(text)}


def main():
    print("=" * 70)
    print("  OCR Engine Comparison — Admission Forms")
    print("=" * 70)

    # Load test data
    data_path = PROJECT_ROOT / "training_data" / "prepared" / "training_data.json"
    with open(data_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    test_recs = [r for r in records if r.get("images") and r.get("fields")
                 and any(Path(p).exists() for p in r.get("images", []))]
    test_recs = test_recs[:3]  # First 3
    print(f"  Testing {len(test_recs)} forms\n")

    all_results = {}

    for idx, rec in enumerate(test_recs):
        img_path = next(p for p in rec["images"] if Path(p).exists())
        fields = {k: v for k, v in rec.get("fields", {}).items() if v and len(v.strip()) >= 2}
        print(f"\n{'━' * 70}")
        print(f"  Form {idx+1}: {Path(img_path).name} ({len(fields)} fields)")
        print(f"{'━' * 70}")

        # Tesseract
        def run_tesseract(p):
            import pytesseract
            from PIL import Image
            img = Image.open(p)
            text = pytesseract.image_to_string(img)
            data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
            confs = [int(c) for c in data["conf"] if int(c) > 0]
            return text, sum(confs) / max(len(confs), 1) / 100.0

        r = evaluate_engine("Tesseract", run_tesseract, img_path, fields)
        if r:
            all_results.setdefault("Tesseract", []).append(r)

        # EasyOCR
        if idx == 0:
            import easyocr
            global_reader = easyocr.Reader(["en"], gpu=False, verbose=False)

        def run_easyocr(p):
            results = global_reader.readtext(p)
            text = " ".join([r[1] for r in results])
            confs = [r[2] for r in results]
            return text, sum(confs) / max(len(confs), 1)

        r = evaluate_engine("EasyOCR", run_easyocr, img_path, fields)
        if r:
            all_results.setdefault("EasyOCR", []).append(r)

    # Summary
    print(f"\n{'═' * 70}")
    print(f"  OVERALL SUMMARY")
    print(f"{'═' * 70}")
    print(f"  {'Engine':<15} {'Exact%':>8} {'Fuzzy%':>8} {'Avg Time':>10} {'Confidence':>12}")
    print(f"  {'─'*15} {'─'*8} {'─'*8} {'─'*10} {'─'*12}")

    for name, results_list in all_results.items():
        total_exact = sum(r["exact"] for r in results_list)
        total_fuzzy = sum(r["fuzzy"] for r in results_list)
        total_fields = sum(r["total"] for r in results_list)
        avg_time = sum(r["time"] for r in results_list) / len(results_list)
        avg_conf = sum(r["conf"] for r in results_list) / len(results_list)
        tf = max(total_fields, 1)
        print(f"  {name:<15} {total_exact/tf:>7.0%} {total_fuzzy/tf:>7.0%} {avg_time:>9.1f}s {avg_conf:>11.2f}")

    # Save
    out_path = PROJECT_ROOT / "training_output" / "engine_comparison.json"
    with open(out_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\n  Saved to: {out_path}")


if __name__ == "__main__":
    main()
