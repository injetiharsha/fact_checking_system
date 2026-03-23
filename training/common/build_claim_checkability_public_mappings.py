import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from training.common.utils import ensure_dir

VALID_LABELS = {
    "factual_claim",
    "personal_statement",
    "opinion",
    "question_or_rewrite",
    "other_uncheckable",
}

CLAIMBUSTER_LABEL_MAP = {
    "1": "factual_claim",
    "0": "other_uncheckable",
    "checkworthy": "factual_claim",
    "check_worthy": "factual_claim",
    "worthy": "factual_claim",
    "non_checkworthy": "other_uncheckable",
    "non-checkworthy": "other_uncheckable",
    "not_worth_checking": "other_uncheckable",
}

CHECKTHAT_LABEL_MAP = {
    "1": "factual_claim",
    "0": "other_uncheckable",
    "checkworthy": "factual_claim",
    "check_worthy": "factual_claim",
    "yes": "factual_claim",
    "not_checkworthy": "other_uncheckable",
    "non_checkworthy": "other_uncheckable",
    "no": "other_uncheckable",
}


def load_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    if path.suffix.lower() == ".jsonl":
        rows = []
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                rows.append(json.loads(line))
        return rows
    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            for key in ("rows", "data", "records", "items"):
                value = payload.get(key)
                if isinstance(value, list):
                    return value
        raise ValueError(f"Unsupported JSON shape in {path}")
    if path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))
    raise ValueError(f"Unsupported input format: {path}")


def pick_text(row: dict) -> str:
    for key in ("text", "Text", "claim", "sentence", "content", "tweet", "utterance", "statement"):
        value = row.get(key)
        if value:
            return " ".join(str(value).split())
    return ""


def pick_label(row: dict) -> str:
    for key in ("mapped_label", "label", "Label", "Verdict", "checkability_label", "checkworthy_label", "check_worthiness"):
        if key in row and row.get(key) is not None:
            return str(row.get(key)).strip()
    return ""


def normalize_with_map(rows: list[dict], source_name: str, label_map: dict[str, str], start_index: int) -> list[dict]:
    normalized = []
    index = start_index
    for row in rows:
        text = pick_text(row)
        raw_label = pick_label(row).strip().lower().replace(" ", "_")
        mapped = label_map.get(raw_label, raw_label)
        if not text or mapped not in VALID_LABELS:
            continue
        normalized.append(
            {
                "id": str(row.get("id") or row.get("sentence_id") or row.get("Sentence_id") or f"{source_name}_{index}"),
                "text": text,
                "label": mapped,
                "source": source_name,
            }
        )
        index += 1
    return normalized


def dedupe(rows: list[dict]) -> list[dict]:
    seen = set()
    output = []
    for row in rows:
        key = (row["text"].casefold(), row["label"])
        if key in seen:
            continue
        seen.add(key)
        output.append(row)
    return output


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build mapped public claim-checkability rows from local dataset exports.")
    parser.add_argument("--claimbuster-file", default=None)
    parser.add_argument("--checkthat-file", default=None)
    parser.add_argument("--output-file", default="data/claim_checkability/seeds/public_mapped_v2.jsonl")
    args = parser.parse_args()

    rows = []
    next_index = 1
    if args.claimbuster_file:
        claimbuster_rows = load_rows(Path(args.claimbuster_file))
        normalized = normalize_with_map(claimbuster_rows, "claimbuster", CLAIMBUSTER_LABEL_MAP, next_index)
        rows.extend(normalized)
        next_index += len(normalized)
    if args.checkthat_file:
        checkthat_rows = load_rows(Path(args.checkthat_file))
        normalized = normalize_with_map(checkthat_rows, "checkthat", CHECKTHAT_LABEL_MAP, next_index)
        rows.extend(normalized)
        next_index += len(normalized)

    rows = dedupe(rows)
    output_path = Path(args.output_file)
    ensure_dir(output_path.parent)
    write_jsonl(output_path, rows)
    print(f"Wrote {len(rows)} mapped public rows to {output_path}")


if __name__ == "__main__":
    main()
