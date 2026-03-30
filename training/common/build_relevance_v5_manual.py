import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from training.common.build_relevance_dataset import MANUAL_RELEVANCE_SEEDS
from training.common.utils import ensure_dir, stratified_split_records


def build_manual_records() -> list[dict]:
    records = []
    next_id = 1
    for seed in MANUAL_RELEVANCE_SEEDS:
        records.append(
            {
                "id": f"relevance_manual_{next_id}",
                "claim": seed["claim"],
                "candidate_sentence": seed["positive"],
                "label": 1,
                "source": seed["source"],
                "selection_origin": "manual_positive_seed",
            }
        )
        next_id += 1
        for negative in seed["negatives"]:
            records.append(
                {
                    "id": f"relevance_manual_{next_id}",
                    "claim": seed["claim"],
                    "candidate_sentence": negative,
                    "label": 0,
                    "source": seed["source"],
                    "selection_origin": "manual_negative_seed",
                }
            )
            next_id += 1
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description="Build manual-only relevance v5 dataset.")
    parser.add_argument("--output-dir", default="data/relevance/v5")
    args = parser.parse_args()

    records = build_manual_records()
    output_dir = ensure_dir(args.output_dir)
    train_rows, val_rows, test_rows = stratified_split_records(
        records,
        label_key="label",
        validation_ratio=0.15,
        test_ratio=0.15,
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
        f"and {len(test_rows)} test manual relevance examples to {output_dir}"
    )


if __name__ == "__main__":
    main()
