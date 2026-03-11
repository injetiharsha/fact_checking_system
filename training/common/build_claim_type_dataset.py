import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from claim_detection.claim_type_classifier import ClaimTypeClassifier
from training.common.utils import ensure_dir, read_json


def infer_label(text: str, classifier: ClaimTypeClassifier) -> tuple[str, float]:
    result = classifier.classify(text)
    return result["type"].value, float(result.get("confidence", 0.0))


def build_records(benchmark_path: Path) -> List[Dict]:
    benchmark = read_json(benchmark_path)
    classifier = ClaimTypeClassifier()
    records = []
    seen = set()
    for idx, row in enumerate(benchmark.get("claims", []), start=1):
        text = str(row.get("claim", "")).strip()
        if not text or text.lower() in seen:
            continue
        seen.add(text.lower())
        label, confidence = infer_label(text, classifier)
        records.append({
            "id": f"claim_type_{idx}",
            "text": text,
            "label": label,
            "source": "benchmark_claim",
            "confidence_hint": round(confidence, 3),
        })
    return records


def split_records(records: List[Dict], validation_ratio: float = 0.1) -> tuple[List[Dict], List[Dict]]:
    if len(records) < 2:
        return records, []
    split_idx = max(1, int(len(records) * (1 - validation_ratio)))
    return records[:split_idx], records[split_idx:]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build weakly labeled claim-type dataset.")
    parser.add_argument("--benchmark", default="parallel_test_results.json")
    parser.add_argument("--output-dir", default="data/claim_type/v1")
    args = parser.parse_args()

    records = build_records(Path(args.benchmark))
    output_dir = ensure_dir(args.output_dir)
    train_rows, val_rows = split_records(records)
    for file_name, rows in (("train.jsonl", train_rows), ("validation.jsonl", val_rows), ("dataset.jsonl", records)):
        output_path = output_dir / file_name
        with output_path.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"Wrote {len(train_rows)} train and {len(val_rows)} validation claim-type examples to {output_dir}")


if __name__ == "__main__":
    main()
