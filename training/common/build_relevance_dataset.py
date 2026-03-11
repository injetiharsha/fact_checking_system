import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from training.common.utils import ensure_dir, read_json


def build_records(benchmark_path: Path) -> List[Dict]:
    benchmark = read_json(benchmark_path)
    records = []
    for row_idx, row in enumerate(benchmark.get("claims", []), start=1):
        claim = str(row.get("claim", "")).strip()
        output = row.get("pipeline_output", {}) or {}
        result_rows = output.get("results", []) if isinstance(output, dict) else []
        if not result_rows:
            continue
        evidence = result_rows[0].get("evidence", []) or []
        for ev_idx, ev in enumerate(evidence, start=1):
            text = str(ev.get("text", "")).strip()
            if not claim or not text:
                continue
            stance = str(ev.get("stance", "")).upper()
            label = 1 if stance in {"SUPPORT", "REFUTE"} and float(ev.get("confidence", 0.0)) >= 0.55 else 0
            records.append({
                "id": f"relevance_{row_idx}_{ev_idx}",
                "claim": claim,
                "candidate_sentence": text,
                "label": label,
                "source": ev.get("source", "unknown"),
                "selection_origin": "selected_evidence",
            })
    return records


def split_records(records: List[Dict], validation_ratio: float = 0.1) -> tuple[List[Dict], List[Dict]]:
    if len(records) < 2:
        return records, []
    split_idx = max(1, int(len(records) * (1 - validation_ratio)))
    return records[:split_idx], records[split_idx:]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build weakly labeled relevance dataset.")
    parser.add_argument("--benchmark", default="parallel_test_results.json")
    parser.add_argument("--output-dir", default="data/relevance/v1")
    args = parser.parse_args()

    records = build_records(Path(args.benchmark))
    output_dir = ensure_dir(args.output_dir)
    train_rows, val_rows = split_records(records)
    for file_name, rows in (("train.jsonl", train_rows), ("validation.jsonl", val_rows), ("dataset.jsonl", records)):
        output_path = output_dir / file_name
        with output_path.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"Wrote {len(train_rows)} train and {len(val_rows)} validation relevance examples to {output_dir}")


if __name__ == "__main__":
    main()
