import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List

from datasets import load_dataset

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from training.common.config import load_yaml_config
from training.common.utils import ensure_dir, stratified_split_records


LABEL_MAPS = {
    "fever": {
        "SUPPORTS": "SUPPORT",
        "REFUTES": "REFUTE",
        "NOT ENOUGH INFO": "NEUTRAL",
    },
    "scifact": {
        "SUPPORT": "SUPPORT",
        "CONTRADICT": "REFUTE",
        "NEUTRAL": "NEUTRAL",
    },
    "mnli": {
        "entailment": "SUPPORT",
        "contradiction": "REFUTE",
        "neutral": "NEUTRAL",
    },
}


def normalize_text(value: Any) -> str:
    return str(value or "").strip()


def extract_records(dataset_key: str, rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized: list[Dict[str, Any]] = []
    # Use 'xnli' label map for all xnli_* keys
    key_for_map = dataset_key
    if dataset_key.startswith('xnli'):
        key_for_map = 'mnli'  # XNLI uses same label mapping as MNLI
    label_map = LABEL_MAPS[key_for_map]

    for idx, row in enumerate(rows, start=1):
        if dataset_key == "fever":
            claim = normalize_text(row.get("claim"))
            evidence_groups = row.get("evidence") or []
            evidence = ""
            if isinstance(evidence_groups, list) and evidence_groups:
                first_group = evidence_groups[0]
                if isinstance(first_group, list) and first_group:
                    evidence = " ".join(normalize_text(part) for part in first_group if part)
            raw_label = normalize_text(row.get("label")).upper()
        elif dataset_key == "scifact":
            claim = normalize_text(row.get("claim"))
            evidence = normalize_text(row.get("evidence"))
            raw_label = normalize_text(row.get("label")).upper()
        elif dataset_key == "mnli":
            claim = normalize_text(row.get("hypothesis"))
            evidence = normalize_text(row.get("premise"))
            raw_label = normalize_text(row.get("label_text")).lower()
        else:
            continue

        label = label_map.get(raw_label)
        if not claim or not evidence or label not in {"SUPPORT", "REFUTE", "NEUTRAL"}:
            continue

        normalized.append(
            {
                "id": f"{dataset_key}_{idx}",
                "claim": claim,
                "evidence": evidence,
                "label": label,
                "source": f"public:{dataset_key}",
                "source_weight": 1.0,
                "weak_label": False,
            }
        )
    return normalized


def load_public_records(config: Dict[str, Any]) -> list[Dict[str, Any]]:
    records: list[Dict[str, Any]] = []
    for source in config.get("sources", []):
        if not source.get("enabled", True):
            continue

        dataset_key = source["key"]
        dataset_name = source["dataset_name"]
        split = source.get("split", "train")
        sample_limit = int(source.get("sample_limit", 0))

        # For XNLI, pass language as positional argument if present
        if dataset_name == "xnli":
            language = None
            if "dataset_kwargs" in source and "language" in source["dataset_kwargs"]:
                language = source["dataset_kwargs"]["language"]
            if language:
                ds = load_dataset(dataset_name, language, split=split)
            else:
                ds = load_dataset(dataset_name, split=split)
        else:
            dataset_kwargs = source.get("dataset_kwargs", {})
            ds = load_dataset(dataset_name, **dataset_kwargs, split=split)

        if sample_limit > 0:
            ds = ds.select(range(min(sample_limit, len(ds))))

        if dataset_key == "mnli" and "label" in ds.column_names and "label_text" not in ds.column_names:
            label_names = ["entailment", "neutral", "contradiction"]

            def with_label_text(row: Dict[str, Any]) -> Dict[str, Any]:
                row["label_text"] = label_names[int(row["label"])]
                return row

            ds = ds.map(with_label_text)

        records.extend(extract_records(dataset_key, ds))
    return records


def read_local_records(path: Path) -> list[Dict[str, Any]]:
    rows: list[Dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Augment local stance data with public datasets.")
    parser.add_argument("--config", default="training/configs/stance_public.yaml")
    parser.add_argument("--local-dataset", default="data/stance/v1/dataset.jsonl")
    parser.add_argument("--output-dir", default="data/stance/v2")
    args = parser.parse_args()

    config = load_yaml_config(args.config)
    local_records = read_local_records(Path(args.local_dataset))
    public_records = load_public_records(config)

    merged = local_records + public_records
    train_rows, validation_rows, test_rows = stratified_split_records(
        merged,
        label_key="label",
        validation_ratio=float(config.get("splits", {}).get("validation_ratio", 0.1)),
        test_ratio=float(config.get("splits", {}).get("test_ratio", 0.1)),
        seed=int(config.get("seed", 42)),
    )

    output_dir = ensure_dir(args.output_dir)
    write_jsonl(output_dir / "train.jsonl", train_rows)
    write_jsonl(output_dir / "validation.jsonl", validation_rows)
    write_jsonl(output_dir / "test.jsonl", test_rows)
    write_jsonl(output_dir / "dataset.jsonl", merged)

    print(
        f"Wrote merged stance dataset to {output_dir} "
        f"(local={len(local_records)}, public={len(public_records)}, total={len(merged)})"
    )


if __name__ == "__main__":
    main()
