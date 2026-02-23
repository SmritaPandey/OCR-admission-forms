"""
Google AI vs Open-Source OCR — Head-to-Head Comparison

Compares accuracy against verified ground-truth field values by scoring
each engine's raw OCR text against the same set of fields.
"""

import json
import os
import sys
import time
from pathlib import Path
from difflib import SequenceMatcher

sys.path.insert(0, str(Path(__file__).parent))
os.environ["PATH"] = r"C:\Program Files\Tesseract-OCR" + os.pathsep + os.environ.get("PATH", "")

PROJECT_ROOT = Path(__file__).parent


def fuzzy_score(value, text):
    if not value or not text:
        return 0.0
    val = value.strip().lower()
    txt = text.lower()
    if val in txt:
        return 1.0
    words = txt.split()
    val_words = val.split()
    best = 0.0
    window = max(len(val_words), 1)
    for i in range(max(len(words) - window + 1, 0)):
        chunk = " ".join(words[i:i + window])
        r = SequenceMatcher(None, val, chunk).ratio()
        best = max(best, r)
    if len(val_words) == 1:
        for w in words:
            r = SequenceMatcher(None, val, w.lower()).ratio()
            best = max(best, r)
    return best


def score_fields(fields, ocr_text):
    exact = fuzzy = total = 0
    field_results = {}
    for k, v in fields.items():
        if not v or len(str(v).strip()) < 2:
            continue
        # Skip doc checklist fields
        if k.startswith("doc_"):
            continue
        total += 1
        s = fuzzy_score(str(v), ocr_text)
        field_results[k] = {"value": v, "score": round(s, 2), "match": "exact" if s >= 0.95 else ("fuzzy" if s >= 0.70 else "miss")}
        if s >= 0.95:
            exact += 1
        if s >= 0.70:
            fuzzy += 1
    return exact, fuzzy, total, field_results


def get_ocr_text_from_images(images, engine="tesseract", reader=None):
    """Run OCR on all available page images and concatenate text."""
    pages = []
    total_time = 0
    for img_path in images:
        if not Path(img_path).exists():
            continue
        if engine == "tesseract":
            import pytesseract
            from PIL import Image
            img = Image.open(img_path)
            start = time.time()
            text = pytesseract.image_to_string(img)
            total_time += time.time() - start
            pages.append(text)
        elif engine == "easyocr":
            start = time.time()
            results = reader.readtext(img_path)
            total_time += time.time() - start
            text = " ".join([r[1] for r in results])
            pages.append(text)
    return "\n\n".join(pages), total_time


def main():
    print("=" * 70)
    print("  GOOGLE AI  vs  OPEN-SOURCE OCR")
    print("  Head-to-Head Accuracy Comparison")
    print("=" * 70)

    # Load verified samples (has Google Vision OCR text + verified fields)
    verified_path = PROJECT_ROOT / "training_data" / "google_ocr" / "verified_samples.json"
    with open(verified_path, "r", encoding="utf-8") as f:
        verified = json.load(f)

    # Load prepared data to find images
    prepared_path = PROJECT_ROOT / "training_data" / "prepared" / "training_data.json"
    with open(prepared_path, "r", encoding="utf-8") as f:
        prepared = json.load(f)

    # Get forms that have images
    forms_with_images = [r for r in prepared if r.get("images") and any(Path(p).exists() for p in r["images"])]

    print(f"\n  Verified Google Vision samples: {len(verified)}")
    print(f"  Forms with images: {len(forms_with_images)}")

    # Initialize EasyOCR
    print("\n  Initializing EasyOCR (one-time model load)...")
    import easyocr
    reader = easyocr.Reader(["en"], gpu=False, verbose=False)

    # ======== Part A: Google Vision accuracy (from verified_samples) ========
    print(f"\n{'━' * 70}")
    print(f"  PART A: Google Vision AI Accuracy (all {len(verified)} verified forms)")
    print(f"{'━' * 70}")

    google_total_exact = google_total_fuzzy = google_total_fields = 0
    for sample in verified:
        gt = sample.get("extracted_fields", {})
        ocr_text = sample.get("raw_ocr_text", "")
        exact, fuzzy, total, details = score_fields(gt, ocr_text)
        google_total_exact += exact
        google_total_fuzzy += fuzzy
        google_total_fields += total

        pct = exact / max(total, 1) * 100
        fpct = fuzzy / max(total, 1) * 100
        print(f"    Form {sample.get('form_id')}: Exact {exact}/{total} ({pct:.0f}%) | Fuzzy {fuzzy}/{total} ({fpct:.0f}%)")

    g_pct = google_total_exact / max(google_total_fields, 1) * 100
    g_fpct = google_total_fuzzy / max(google_total_fields, 1) * 100
    print(f"\n    📊 Google Vision Average: Exact {g_pct:.1f}% | Fuzzy {g_fpct:.1f}%")

    # ======== Part B: Open-source on same prepared forms (single pages) ========
    # Pick 5 forms for direct comparison
    test_forms = forms_with_images[:5]
    print(f"\n{'━' * 70}")
    print(f"  PART B: Open-Source OCR ({len(test_forms)} forms, page 1 only)")
    print(f"{'━' * 70}")

    tess_exact = tess_fuzzy = tess_total = 0
    easy_exact = easy_fuzzy = easy_total = 0
    tess_times = []
    easy_times = []

    for idx, rec in enumerate(test_forms):
        fields = {k: v for k, v in rec.get("fields", {}).items()
                  if v and len(str(v).strip()) >= 2 and not k.startswith("doc_")}
        if not fields:
            continue

        images = [p for p in rec["images"] if Path(p).exists()]
        if not images:
            continue

        # Use first page only (same conditions)
        img = images[0]
        fname = Path(img).name
        print(f"\n  Form {idx+1}: {fname} ({len(fields)} fields)")

        # Tesseract
        try:
            text, t = get_ocr_text_from_images([img], "tesseract")
            e, f_, tot, _ = score_fields(fields, text)
            tess_exact += e
            tess_fuzzy += f_
            tess_total += tot
            tess_times.append(t)
            print(f"    [Tesseract]  Exact: {e}/{tot} ({e/max(tot,1)*100:.0f}%) | Fuzzy: {f_}/{tot} ({f_/max(tot,1)*100:.0f}%) | {t:.1f}s")
        except Exception as ex:
            print(f"    [Tesseract]  ERROR: {ex}")

        # EasyOCR
        try:
            text, t = get_ocr_text_from_images([img], "easyocr", reader)
            e, f_, tot, _ = score_fields(fields, text)
            easy_exact += e
            easy_fuzzy += f_
            easy_total += tot
            easy_times.append(t)
            print(f"    [EasyOCR]    Exact: {e}/{tot} ({e/max(tot,1)*100:.0f}%) | Fuzzy: {f_}/{tot} ({f_/max(tot,1)*100:.0f}%) | {t:.1f}s")
        except Exception as ex:
            print(f"    [EasyOCR]    ERROR: {ex}")

    # ======== Part C: Full multi-page OCR for fairer comparison ========
    # Run ALL pages through Tesseract/EasyOCR for the first 2 forms
    multi_forms = forms_with_images[:2]
    print(f"\n{'━' * 70}")
    print(f"  PART C: Multi-Page OCR ({len(multi_forms)} forms, ALL pages)")
    print(f"{'━' * 70}")

    tess_mp_exact = tess_mp_fuzzy = tess_mp_total = 0
    easy_mp_exact = easy_mp_fuzzy = easy_mp_total = 0

    for idx, rec in enumerate(multi_forms):
        fields = {k: v for k, v in rec.get("fields", {}).items()
                  if v and len(str(v).strip()) >= 2 and not k.startswith("doc_")}
        images = [p for p in rec["images"] if Path(p).exists()]

        print(f"\n  Form {idx+1}: {len(images)} pages, {len(fields)} fields")

        # Tesseract all pages
        try:
            text, t = get_ocr_text_from_images(images, "tesseract")
            e, f_, tot, _ = score_fields(fields, text)
            tess_mp_exact += e
            tess_mp_fuzzy += f_
            tess_mp_total += tot
            print(f"    [Tesseract]  Exact: {e}/{tot} ({e/max(tot,1)*100:.0f}%) | Fuzzy: {f_}/{tot} ({f_/max(tot,1)*100:.0f}%) | {t:.1f}s")
        except Exception as ex:
            print(f"    [Tesseract]  ERROR: {ex}")

        # EasyOCR all pages
        try:
            text, t = get_ocr_text_from_images(images, "easyocr", reader)
            e, f_, tot, _ = score_fields(fields, text)
            easy_mp_exact += e
            easy_mp_fuzzy += f_
            easy_mp_total += tot
            print(f"    [EasyOCR]    Exact: {e}/{tot} ({e/max(tot,1)*100:.0f}%) | Fuzzy: {f_}/{tot} ({f_/max(tot,1)*100:.0f}%) | {t:.1f}s")
        except Exception as ex:
            print(f"    [EasyOCR]    ERROR: {ex}")

    # ======== FINAL SUMMARY TABLE ========
    print(f"\n{'═' * 70}")
    print(f"  ⭐ FINAL COMPARISON RESULTS")
    print(f"{'═' * 70}")
    print(f"\n  {'Engine':<28} {'Exact Match':>12} {'Fuzzy Match':>12} {'Speed':>8}")
    print(f"  {'─' * 28} {'─' * 12} {'─' * 12} {'─' * 8}")

    gt = max(google_total_fields, 1)
    tt = max(tess_total, 1)
    et = max(easy_total, 1)
    tmt = max(tess_mp_total, 1)
    emt = max(easy_mp_total, 1)

    print(f"  {'Google Vision AI (multi-pg)':<28} {google_total_exact/gt*100:>10.1f}% {google_total_fuzzy/gt*100:>10.1f}% {'cloud':>8}")
    if tess_total:
        avg_t = sum(tess_times) / max(len(tess_times), 1)
        print(f"  {'Tesseract (single page)':<28} {tess_exact/tt*100:>10.1f}% {tess_fuzzy/tt*100:>10.1f}% {avg_t:>6.1f}s")
    if easy_total:
        avg_e = sum(easy_times) / max(len(easy_times), 1)
        print(f"  {'EasyOCR (single page)':<28} {easy_exact/et*100:>10.1f}% {easy_fuzzy/et*100:>10.1f}% {avg_e:>6.1f}s")
    if tess_mp_total:
        print(f"  {'Tesseract (multi-page)':<28} {tess_mp_exact/tmt*100:>10.1f}% {tess_mp_fuzzy/tmt*100:>10.1f}% {'local':>8}")
    if easy_mp_total:
        print(f"  {'EasyOCR (multi-page)':<28} {easy_mp_exact/emt*100:>10.1f}% {easy_mp_fuzzy/emt*100:>10.1f}% {'local':>8}")

    print(f"\n  💡 Key Insight: Google Vision scores higher because it processes")
    print(f"     ALL pages (including certificates, marksheets, Aadhaar) which")
    print(f"     contain many of the ground-truth field values.")

    # Save
    out = {
        "google_vision": {
            "exact_rate": round(google_total_exact/gt, 3),
            "fuzzy_rate": round(google_total_fuzzy/gt, 3),
            "total_fields": google_total_fields,
        },
        "tesseract_single_page": {
            "exact_rate": round(tess_exact/tt, 3) if tess_total else None,
            "fuzzy_rate": round(tess_fuzzy/tt, 3) if tess_total else None,
            "total_fields": tess_total,
        },
        "easyocr_single_page": {
            "exact_rate": round(easy_exact/et, 3) if easy_total else None,
            "fuzzy_rate": round(easy_fuzzy/et, 3) if easy_total else None,
            "total_fields": easy_total,
        },
        "tesseract_multi_page": {
            "exact_rate": round(tess_mp_exact/tmt, 3) if tess_mp_total else None,
            "fuzzy_rate": round(tess_mp_fuzzy/tmt, 3) if tess_mp_total else None,
            "total_fields": tess_mp_total,
        },
        "easyocr_multi_page": {
            "exact_rate": round(easy_mp_exact/emt, 3) if easy_mp_total else None,
            "fuzzy_rate": round(easy_mp_fuzzy/emt, 3) if easy_mp_total else None,
            "total_fields": easy_mp_total,
        },
    }
    out_path = PROJECT_ROOT / "training_output" / "google_vs_opensource_comparison.json"
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\n  📊 Saved to: {out_path}")


if __name__ == "__main__":
    main()
