import argparse
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

import sys
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from training.common.utils import ensure_dir, read_json, stratified_split_records


SEED = 42


def read_jsonl(path: str | Path) -> list[dict]:
    rows = []
    file_path = Path(path)
    if not file_path.exists():
        return rows
    with file_path.open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def normalize_record(row: dict, idx_prefix: str, idx: int) -> dict:
    return {
        "id": row.get("id") or f"{idx_prefix}_{idx}",
        "claim": row["claim"],
        "candidate_sentence": row["candidate_sentence"],
        "label": int(row["label"]),
        "source": row.get("source", idx_prefix),
        "source_url": row.get("source_url"),
        "selection_origin": row.get("selection_origin", idx_prefix),
    }


def load_existing_records() -> list[dict]:
    records = []
    for idx, row in enumerate(read_jsonl("data/relevance/v9/dataset.jsonl"), start=1):
        records.append(normalize_record(row, "relevance_v9", idx))
    offset = len(records)
    for idx, row in enumerate(read_jsonl("data/relevance/v12_source_residual/dataset.jsonl"), start=1):
        records.append(normalize_record(row, "relevance_v12", offset + idx))
    offset = len(records)
    for idx, row in enumerate(read_jsonl("data/relevance/seeds/india_official_curated_v13.jsonl"), start=1):
        records.append(normalize_record(row, "india_v13", offset + idx))
    offset = len(records)
    for idx, row in enumerate(read_jsonl("data/relevance/seeds/source_quality_curated_v13.jsonl"), start=1):
        records.append(normalize_record(row, "source_quality_v13", offset + idx))
    offset = len(records)
    for idx, row in enumerate(read_jsonl("data/relevance/seeds/india_multilingual_news_curated_v13.jsonl"), start=1):
        records.append(normalize_record(row, "india_multilingual_news_v13", offset + idx))
    return records


def answer_text(answer: dict) -> str:
    explanation = str(answer.get("boolean_explanation") or "").strip()
    if len(explanation.split()) >= 6:
        return explanation
    value = str(answer.get("answer") or "").strip()
    if len(value.split()) >= 6:
        return value
    return ""


def build_averitec_records(max_claims: int = 300, negatives_per_positive: int = 2) -> list[dict]:
    rng = random.Random(SEED)
    rows = []
    raw = []
    for path in ("data/public/averitec/train.json", "data/public/averitec/dev.json"):
        file_path = Path(path)
        if file_path.exists():
            raw.extend(read_json(file_path))
    positives = []
    claim_positive_pairs = []
    for item in raw:
        claim = str(item.get("claim") or "").strip()
        if not claim:
            continue
        candidate = ""
        for question in item.get("questions", []):
            for answer in question.get("answers", []):
                candidate = answer_text(answer)
                if candidate:
                    break
            if candidate:
                break
        if not candidate:
            continue
        claim_positive_pairs.append((claim, candidate, item))
        positives.append(candidate)
    rng.shuffle(claim_positive_pairs)
    claim_positive_pairs = claim_positive_pairs[:max_claims]

    next_id = 1
    for claim, candidate, item in claim_positive_pairs:
        source_url = item.get("fact_checking_article") or item.get("original_claim_url")
        rows.append(
            {
                "id": f"averitec_v13_{next_id}",
                "claim": claim,
                "candidate_sentence": candidate,
                "label": 1,
                "source": "averitec_v13",
                "source_url": source_url,
                "selection_origin": "averitec_positive_v13",
            }
        )
        next_id += 1
        distractors = [p for p in positives if p != candidate and p.strip()]
        rng.shuffle(distractors)
        for negative in distractors[:negatives_per_positive]:
            rows.append(
                {
                    "id": f"averitec_v13_{next_id}",
                    "claim": claim,
                    "candidate_sentence": negative,
                    "label": 0,
                    "source": "averitec_v13",
                    "source_url": source_url,
                    "selection_origin": "averitec_swapped_negative_v13",
                }
            )
            next_id += 1
    return rows


def dedupe(records: list[dict]) -> list[dict]:
    seen = set()
    out = []
    for row in records:
        key = (row["claim"], row["candidate_sentence"], int(row["label"]))
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Build broad relevance v13 dataset.")
    parser.add_argument("--output-dir", default="data/relevance/v13_broad")
    parser.add_argument("--max-averitec-claims", type=int, default=300)
    args = parser.parse_args()

    records = load_existing_records()
    records.extend(build_averitec_records(max_claims=args.max_averitec_claims))
    records = dedupe(records)

    output_dir = ensure_dir(args.output_dir)
    train_rows, val_rows, test_rows = stratified_split_records(
        records,
        label_key="label",
        validation_ratio=0.15,
        test_ratio=0.15,
        seed=SEED,
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

    metadata = {
        "dataset_name": "relevance_v13_broad",
        "record_count": len(records),
        "train_count": len(train_rows),
        "validation_count": len(val_rows),
        "test_count": len(test_rows),
        "source_breakdown": {
            "relevance_v9": sum(1 for row in records if row["source"].startswith("manual") or row["source"].startswith("internet") or row["source"] == "phase2_residual_seed"),
            "india_official_curated_v13": sum(1 for row in records if row["source"] == "india_official_curated_v13"),
            "source_quality_curated_v13": sum(1 for row in records if row["source"] == "source_quality_curated_v13"),
            "india_multilingual_news_curated_v13": sum(1 for row in records if row["source"] == "india_multilingual_news_curated_v13"),
            "averitec_v13": sum(1 for row in records if row["source"] == "averitec_v13"),
        },
    }
    with (output_dir / "metadata.json").open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, ensure_ascii=False, indent=2)

    print(
        f"Wrote {len(train_rows)} train, {len(val_rows)} validation, and {len(test_rows)} test records to {output_dir}"
    )


if __name__ == "__main__":
    main()
