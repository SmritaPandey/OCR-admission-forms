from __future__ import annotations

import argparse
import asyncio
import json
import time
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Iterable, List, Optional, Tuple

from backend.config import settings
from backend.ocr import get_ocr_provider
from backend.ocr.ocr_factory import OCRFactory
from backend.utils.file_handler import (
    get_file_extension,
    load_all_pdf_pages,
    load_image,
)


@dataclass
class Sample:
    sample_id: str
    file_path: Path
    annotation: Dict[str, Any]

    @property
    def fields(self) -> Dict[str, Any]:
        return self.annotation.get("fields", {})

    @property
    def form_type(self) -> Optional[str]:
        return self.annotation.get("form_type")


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def discover_samples(
    raw_dir: Path,
    labels_dir: Path,
    only_ids: Optional[Iterable[str]] = None,
    limit: Optional[int] = None,
) -> List[Sample]:
    if not labels_dir.exists():
        raise FileNotFoundError(f"Labels directory not found: {labels_dir}")
    if not raw_dir.exists():
        raise FileNotFoundError(f"Raw samples directory not found: {raw_dir}")

    include_ids = {sample_id.lower() for sample_id in only_ids} if only_ids else None
    samples: List[Sample] = []

    for label_path in sorted(labels_dir.glob("*.json")):
        sample_id = label_path.stem
        if include_ids and sample_id.lower() not in include_ids:
            continue

        annotation = json.loads(label_path.read_text(encoding="utf-8"))
        filename = annotation.get("file") or annotation.get("filename")

        candidate_paths: List[Path] = []
        if filename:
            candidate = raw_dir / filename
            if candidate.exists():
                candidate_paths.append(candidate)
        else:
            candidate_paths.extend(sorted(raw_dir.glob(f"{sample_id}.*")))

        existing_paths = [path for path in candidate_paths if path.exists()]
        if not existing_paths:
            raise FileNotFoundError(
                f"No matching raw file found for sample '{sample_id}'. "
                f"Specify 'file' in {label_path.name} or ensure the raw file "
                f"uses the same stem."
            )

        sample = Sample(sample_id=sample_id, file_path=existing_paths[0], annotation=annotation)
        samples.append(sample)

        if limit and len(samples) >= limit:
            break

    if not samples:
        raise ValueError("No samples discovered. Check dataset directories or filters.")

    return samples


async def _extract_file_with_provider(
    provider_name: str,
    file_path: Path,
) -> Dict[str, Any]:
    provider = get_ocr_provider(provider_name)
    extension = get_file_extension(str(file_path))

    if extension == "pdf":
        pages = load_all_pdf_pages(str(file_path))
        all_raw_text: List[str] = []
        all_confidences: List[float] = []
        page_results: List[Dict[str, Any]] = []

        for page_index, page_image in enumerate(pages, start=1):
            if provider_name == "tesseract":
                page_result = await provider.extract_text(page_image, preprocess=True)
            else:
                page_result = await provider.extract_text(page_image)

            text_fragment = page_result.get("raw_text", "")
            if text_fragment:
                all_raw_text.append(f"\n--- Page {page_index} ---\n{text_fragment}")
            confidence = page_result.get("confidence")
            if isinstance(confidence, (int, float)):
                all_confidences.append(float(confidence))
            page_results.append(
                {
                    "page": page_index,
                    "raw_text": text_fragment,
                    "confidence": confidence or 0.0,
                }
            )

        combined_text = "\n".join(all_raw_text)
        avg_confidence = mean(all_confidences) if all_confidences else 0.0

        return {
            "raw_text": combined_text,
            "confidence": round(avg_confidence, 2),
            "structured_data": None,
            "provider": provider_name,
            "pages_processed": len(page_results),
            "page_results": page_results,
        }

    image = load_image(str(file_path))
    if provider_name == "tesseract":
        result = await provider.extract_text(image, preprocess=True)
    else:
        result = await provider.extract_text(image)

    result.setdefault("pages_processed", 1)
    result.setdefault(
        "page_results",
        [
            {
                "page": 1,
                "raw_text": result.get("raw_text", ""),
                "confidence": result.get("confidence", 0.0),
            }
        ],
    )
    result.setdefault("provider", provider_name)
    return result


def _evaluate_fields(
    sample: Sample,
    extraction: Dict[str, Any],
) -> Tuple[Optional[float], Optional[float], List[Dict[str, Any]]]:
    expected_fields = sample.fields
    if not expected_fields:
        return None, None, []

    structured_data: Dict[str, Any] = extraction.get("structured_data") or {}
    raw_text = extraction.get("raw_text", "") or ""

    if not structured_data and sample.form_type:
        try:
            from backend.utils.form_parser import parse_form_text

            structured_data = parse_form_text(raw_text, form_type=sample.form_type) or {}
        except Exception:
            structured_data = structured_data or {}

    field_results: List[Dict[str, Any]] = []
    ratios: List[float] = []
    exact_matches = 0

    raw_text_norm = raw_text.lower()

    for field_name, expected in expected_fields.items():
        expected_norm = _normalize_text(expected)
        if not expected_norm:
            continue

        actual_value = structured_data.get(field_name)
        actual_norm = _normalize_text(actual_value)

        ratio = SequenceMatcher(None, expected_norm, actual_norm).ratio() if actual_norm else 0.0
        found_in_raw = expected_norm in raw_text_norm

        # Treat raw-text hits as partial credit if structured data is missing
        if not actual_norm and found_in_raw:
            ratio = max(ratio, 0.8)

        exact = ratio >= 0.999
        if exact:
            exact_matches += 1

        ratios.append(ratio)
        field_results.append(
            {
                "field": field_name,
                "expected": expected,
                "actual": actual_value,
                "similarity": round(ratio, 3),
                "exact_match": exact,
                "found_in_raw": found_in_raw,
            }
        )

    if not field_results:
        return None, None, []

    avg_similarity = mean(ratios) if ratios else 0.0
    exact_rate = exact_matches / len(field_results) if field_results else 0.0

    return avg_similarity, exact_rate, field_results


async def benchmark_provider(
    provider_name: str,
    samples: List[Sample],
) -> Dict[str, Any]:
    provider_metrics: List[Dict[str, Any]] = []
    confidences: List[float] = []
    field_scores: List[float] = []
    exact_rates: List[float] = []
    durations_ms: List[float] = []
    failures = 0

    for sample in samples:
        start = time.perf_counter()
        try:
            extraction = await _extract_file_with_provider(provider_name, sample.file_path)
            duration_ms = (time.perf_counter() - start) * 1000
            durations_ms.append(duration_ms)

            avg_similarity, exact_rate, field_details = _evaluate_fields(sample, extraction)

            confidence = extraction.get("confidence")
            if isinstance(confidence, (int, float)):
                confidences.append(float(confidence))

            if avg_similarity is not None:
                field_scores.append(avg_similarity)
            if exact_rate is not None:
                exact_rates.append(exact_rate)

            provider_metrics.append(
                {
                    "sample_id": sample.sample_id,
                    "file": str(sample.file_path),
                    "confidence": extraction.get("confidence"),
                    "avg_field_similarity": avg_similarity,
                    "exact_match_rate": exact_rate,
                    "processing_time_ms": round(duration_ms, 2),
                    "fields": field_details,
                }
            )
        except Exception as exc:
            failures += 1
            provider_metrics.append(
                {
                    "sample_id": sample.sample_id,
                    "file": str(sample.file_path),
                    "error": str(exc),
                }
            )

    summary = {
        "provider": provider_name,
        "samples_evaluated": len(samples),
        "avg_confidence": round(mean(confidences), 2) if confidences else None,
        "avg_field_similarity": round(mean(field_scores), 3) if field_scores else None,
        "avg_exact_match_rate": round(mean(exact_rates), 3) if exact_rates else None,
        "avg_processing_time_ms": round(mean(durations_ms), 2) if durations_ms else None,
        "failures": failures,
        "details": provider_metrics,
    }
    return summary


def build_cli() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Benchmark OCR providers against the curated admission-form dataset."
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=Path("data/samples/raw"),
        help="Directory containing raw sample files.",
    )
    parser.add_argument(
        "--labels-dir",
        type=Path,
        default=Path("data/samples/labels"),
        help="Directory containing JSON annotations for samples.",
    )
    parser.add_argument(
        "--providers",
        nargs="+",
        help="Explicit list of providers to benchmark. Defaults to OCR_BENCHMARK_PROVIDERS or enabled providers.",
    )
    parser.add_argument(
        "--only",
        nargs="+",
        help="Optional list of sample IDs (without extension) to include.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit the number of samples processed.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path to write the detailed benchmark report JSON.",
    )
    return parser


async def run_benchmark(args: argparse.Namespace) -> Dict[str, Any]:
    samples = discover_samples(args.raw_dir, args.labels_dir, only_ids=args.only, limit=args.limit)

    enabled_providers = set(OCRFactory.get_available_providers())
    if args.providers:
        requested = [provider.lower() for provider in args.providers]
    elif settings.OCR_BENCHMARK_PROVIDERS:
        requested = [provider.lower() for provider in settings.OCR_BENCHMARK_PROVIDERS]
    else:
        # Default to all enabled providers if no specific list is provided
        requested = sorted(enabled_providers)

    missing = [provider for provider in requested if provider not in enabled_providers]
    if missing:
        raise ValueError(
            f"Providers not available or disabled: {', '.join(missing)}. "
            f"Enabled providers: {', '.join(sorted(enabled_providers)) or 'none'}."
        )

    report = []
    for provider_name in requested:
        summary = await benchmark_provider(provider_name, samples)
        report.append(summary)

    return {
        "samples": [sample.sample_id for sample in samples],
        "providers": report,
    }


def print_summary(report: Dict[str, Any]) -> None:
    print(f"Evaluated samples: {', '.join(report['samples'])}")
    for provider_summary in report["providers"]:
        provider = provider_summary["provider"]
        avg_conf = provider_summary["avg_confidence"]
        avg_sim = provider_summary["avg_field_similarity"]
        exact_rate = provider_summary["avg_exact_match_rate"]
        avg_time = provider_summary["avg_processing_time_ms"]

        print(f"\nProvider: {provider}")
        print(f"  Avg confidence:       {avg_conf if avg_conf is not None else 'n/a'}")
        print(f"  Avg field similarity: {avg_sim if avg_sim is not None else 'n/a'}")
        print(f"  Exact match rate:     {exact_rate if exact_rate is not None else 'n/a'}")
        print(f"  Avg processing (ms):  {avg_time if avg_time is not None else 'n/a'}")


def main() -> None:
    parser = build_cli()
    args = parser.parse_args()

    report = asyncio.run(run_benchmark(args))
    print_summary(report)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\nDetailed report written to {args.output}")


if __name__ == "__main__":
    main()

