import argparse
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from training.common.utils import ensure_dir, stratified_split_records


V1_SEED_RECORDS = [
    {"text": "The Earth revolves around the Sun.", "label": "factual_claim", "source": "seed_v1"},
    {"text": "Mars has two moons.", "label": "factual_claim", "source": "seed_v1"},
    {"text": "The Berlin Wall fell in 1989.", "label": "factual_claim", "source": "seed_v1"},
    {"text": "Water boils at 100 degrees Celsius at sea level.", "label": "factual_claim", "source": "seed_v1"},
    {"text": "The moon landing was faked.", "label": "factual_claim", "source": "seed_v1"},
    {"text": "Climate change is a hoax.", "label": "factual_claim", "source": "seed_v1"},
    {"text": "India's inflation was below 4% in 2024.", "label": "factual_claim", "source": "seed_v1"},
    {"text": "Saturn has rings.", "label": "factual_claim", "source": "seed_v1"},
    {"text": "The Sun is a star.", "label": "factual_claim", "source": "seed_v1"},
    {"text": "The Amazon River is the longest river in the world.", "label": "factual_claim", "source": "seed_v1"},
    {"text": "This is me.", "label": "personal_statement", "source": "seed_v1"},
    {"text": "This is us.", "label": "personal_statement", "source": "seed_v1"},
    {"text": "My name is Rahul.", "label": "personal_statement", "source": "seed_v1"},
    {"text": "I am happy today.", "label": "personal_statement", "source": "seed_v1"},
    {"text": "I feel tired.", "label": "personal_statement", "source": "seed_v1"},
    {"text": "I love this song.", "label": "personal_statement", "source": "seed_v1"},
    {"text": "I hate Mondays.", "label": "personal_statement", "source": "seed_v1"},
    {"text": "This is my bike.", "label": "personal_statement", "source": "seed_v1"},
    {"text": "I am from Hyderabad.", "label": "personal_statement", "source": "seed_v1"},
    {"text": "I'm with my friends.", "label": "personal_statement", "source": "seed_v1"},
    {"text": "This movie is amazing.", "label": "opinion", "source": "seed_v1"},
    {"text": "Chocolate is the best dessert.", "label": "opinion", "source": "seed_v1"},
    {"text": "That policy is terrible.", "label": "opinion", "source": "seed_v1"},
    {"text": "This phone has a great camera.", "label": "opinion", "source": "seed_v1"},
    {"text": "I think this design looks better.", "label": "opinion", "source": "seed_v1"},
    {"text": "In my opinion, the article is unfair.", "label": "opinion", "source": "seed_v1"},
    {"text": "This is the greatest team ever.", "label": "opinion", "source": "seed_v1"},
    {"text": "The new logo looks awful.", "label": "opinion", "source": "seed_v1"},
    {"text": "The coach made a brilliant decision.", "label": "opinion", "source": "seed_v1"},
    {"text": "This restaurant is overrated.", "label": "opinion", "source": "seed_v1"},
    {"text": "What happened in Berlin?", "label": "question_or_rewrite", "source": "seed_v1"},
    {"text": "Is climate change real?", "label": "question_or_rewrite", "source": "seed_v1"},
    {"text": "Did NASA fake the moon landing?", "label": "question_or_rewrite", "source": "seed_v1"},
    {"text": "Can humans breathe in space?", "label": "question_or_rewrite", "source": "seed_v1"},
    {"text": "Who won the match yesterday?", "label": "question_or_rewrite", "source": "seed_v1"},
    {"text": "Was the Great Wall visible from space?", "label": "question_or_rewrite", "source": "seed_v1"},
    {"text": "Where is the official notice?", "label": "question_or_rewrite", "source": "seed_v1"},
    {"text": "How many moons does Mars have?", "label": "question_or_rewrite", "source": "seed_v1"},
    {"text": "Is this true?", "label": "question_or_rewrite", "source": "seed_v1"},
    {"text": "Could 5G spread coronavirus?", "label": "question_or_rewrite", "source": "seed_v1"},
    {"text": "wow", "label": "other_uncheckable", "source": "seed_v1"},
    {"text": "hello there", "label": "other_uncheckable", "source": "seed_v1"},
    {"text": "nice pic", "label": "other_uncheckable", "source": "seed_v1"},
    {"text": "lol that's wild", "label": "other_uncheckable", "source": "seed_v1"},
    {"text": "breaking", "label": "other_uncheckable", "source": "seed_v1"},
    {"text": "unbelievable", "label": "other_uncheckable", "source": "seed_v1"},
    {"text": "so true", "label": "other_uncheckable", "source": "seed_v1"},
    {"text": "read this", "label": "other_uncheckable", "source": "seed_v1"},
    {"text": "must watch", "label": "other_uncheckable", "source": "seed_v1"},
    {"text": "viral video", "label": "other_uncheckable", "source": "seed_v1"},
]

VALID_LABELS = {
    "factual_claim",
    "personal_statement",
    "opinion",
    "question_or_rewrite",
    "other_uncheckable",
}


def load_jsonl_records(path: Path) -> list[dict]:
    rows = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def normalize_records(rows: list[dict], source_name: str, start_index: int = 1) -> list[dict]:
    normalized = []
    local_index = start_index
    for row in rows:
        text = " ".join(str(row.get("text", "")).split())
        label = str(row.get("label", "")).strip()
        if not text or label not in VALID_LABELS:
            continue
        record_id = str(row.get("id") or f"{source_name}_{local_index}")
        normalized.append(
            {
                "id": record_id,
                "text": text,
                "label": label,
                "source": str(row.get("source") or source_name),
            }
        )
        local_index += 1
    return normalized


def dedupe_records(rows: list[dict]) -> list[dict]:
    seen = set()
    deduped = []
    for row in rows:
        key = (row["text"].casefold(), row["label"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def cap_by_label(rows: list[dict], max_per_label: int, seed: int = 42) -> list[dict]:
    if not max_per_label or max_per_label <= 0:
        return rows
    rng = random.Random(seed)
    buckets = defaultdict(list)
    for row in rows:
        buckets[row['label']].append(row)
    output = []
    for label, bucket in buckets.items():
        if len(bucket) > max_per_label:
            rng.shuffle(bucket)
            bucket = bucket[:max_per_label]
        output.extend(bucket)
    return output


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build claim-checkability dataset.")
    parser.add_argument("--version", default="v1", choices=["v1", "v2"])
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--local-curated-file", default="data/claim_checkability/seeds/local_curated_v2.jsonl")
    parser.add_argument("--public-file", default="data/claim_checkability/seeds/public_mapped_v2.jsonl")
    parser.add_argument("--public-cap-per-label", type=int, default=400)
    args = parser.parse_args()

    output_dir = Path(args.output_dir) if args.output_dir else Path(f"data/claim_checkability/{args.version}")
    output_dir = ensure_dir(output_dir)

    if args.version == "v1":
        records = normalize_records(V1_SEED_RECORDS, "seed_v1")
        public_rows = []
    else:
        records = normalize_records(V1_SEED_RECORDS, "seed_v1")
        records.extend(normalize_records(load_jsonl_records(Path(args.local_curated_file)), "local_curated_v2"))
        public_rows = normalize_records(load_jsonl_records(Path(args.public_file)), "public_mapped_v2")
        public_rows = cap_by_label(public_rows, args.public_cap_per_label)
        records.extend(public_rows)
        records = dedupe_records(records)

    train_rows, val_rows, test_rows = stratified_split_records(
        records,
        label_key="label",
        validation_ratio=0.15,
        test_ratio=0.15,
    )

    write_jsonl(output_dir / "train.jsonl", train_rows)
    write_jsonl(output_dir / "validation.jsonl", val_rows)
    write_jsonl(output_dir / "test.jsonl", test_rows)
    write_jsonl(output_dir / "dataset.jsonl", records)

    metadata = {
        "version": args.version,
        "total_rows": len(records),
        "train_rows": len(train_rows),
        "validation_rows": len(val_rows),
        "test_rows": len(test_rows),
        "label_distribution": dict(Counter(row["label"] for row in records)),
        "sources": dict(Counter(row["source"] for row in records)),
        "local_curated_file": args.local_curated_file if args.version == "v2" else None,
        "public_file": args.public_file if args.version == "v2" else None,
        "public_cap_per_label": args.public_cap_per_label if args.version == "v2" else None,
        "public_rows_used": len(public_rows) if args.version == "v2" else 0,
    }
    (output_dir / "metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")

    print(
        f"Wrote {len(train_rows)} train, {len(val_rows)} validation, and {len(test_rows)} test rows to {output_dir}"
    )
    print("Label distribution:", metadata["label_distribution"])


if __name__ == "__main__":
    main()
