import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from training.common.utils import ensure_dir, read_json, stratified_split_records


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
            label = str(ev.get("stance", "")).upper()
            if not claim or not text or label not in {"SUPPORT", "REFUTE", "NEUTRAL"}:
                continue
            records.append({
                "id": f"stance_{row_idx}_{ev_idx}",
                "claim": claim,
                "evidence": text,
                "label": label,
                "source": ev.get("source", "unknown"),
                "source_weight": float(ev.get("weight", 0.0)),
                "weak_label": True,
            })
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description="Build weakly labeled stance dataset.")
    parser.add_argument("--benchmark", default="parallel_test_results.json")
    parser.add_argument("--output-dir", default="data/stance/v1")
    args = parser.parse_args()

    records = build_records(Path(args.benchmark))
    output_dir = ensure_dir(args.output_dir)
    train_rows, val_rows, test_rows = stratified_split_records(
        records,
        label_key="label",
        validation_ratio=0.1,
        test_ratio=0.1,
    )
    for file_name, rows in (
        ("train.jsonl", train_rows),
        ("validation.jsonl", val_rows),
        ("test.jsonl", test_rows),
        ("dataset.jsonl", records),
    ):
        output_path = output_dir / file_name
        with output_path.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(
        f"Wrote {len(train_rows)} train, {len(val_rows)} validation, "
        f"and {len(test_rows)} test stance examples to {output_dir}"
    )


if __name__ == "__main__":
    main()
