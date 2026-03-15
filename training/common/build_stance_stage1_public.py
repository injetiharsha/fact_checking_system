import argparse
import json
import os
import sys
from pathlib import Path

from datasets import load_dataset

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from training.common.utils import ensure_dir


def _configure_project_local_cache(project_root: Path) -> Path:
    model_cache = project_root / ".venv" / "model_cache"
    dataset_cache = project_root / ".venv" / "dataset_cache"
    hf_home = project_root / ".venv" / "hf_home"
    hub_cache = model_cache / "hub"
    transformers_cache = model_cache / "transformers"
    sentence_cache = model_cache / "sentence_transformers"
    for path in (model_cache, dataset_cache, hf_home, hub_cache, transformers_cache, sentence_cache):
        path.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("HF_HOME", str(hf_home))
    os.environ.setdefault("HF_DATASETS_CACHE", str(dataset_cache))
    os.environ.setdefault("HUGGINGFACE_HUB_CACHE", str(hub_cache))
    os.environ.setdefault("TRANSFORMERS_CACHE", str(transformers_cache))
    os.environ.setdefault("SENTENCE_TRANSFORMERS_HOME", str(sentence_cache))
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    return dataset_cache


def _write_jsonl(path: Path, rows) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _append_rows(target, rows, prefix, label_mapper, claim_key, evidence_key, source_name, limit=None):
    next_index = len(target) + 1
    added = 0
    for row in rows:
        label = label_mapper(row)
        if label is None:
            continue
        claim = str(row.get(claim_key) or "").strip()
        evidence = str(row.get(evidence_key) or "").strip()
        if not claim or not evidence:
            continue
        target.append({
            "id": f"{prefix}_{next_index}",
            "claim": claim,
            "evidence": evidence,
            "label": label,
            "source": source_name,
            "source_weight": 1.0,
            "weak_label": False,
        })
        next_index += 1
        added += 1
        if limit is not None and added >= limit:
            break


def main() -> None:
    parser = argparse.ArgumentParser(description="Build stage-1 public stance dataset from cached Hugging Face corpora.")
    parser.add_argument("--output-dir", default="data/stance/stage1_public_small")
    parser.add_argument("--vitaminc-train-limit", type=int, default=100000)
    parser.add_argument("--anli-train-limit-per-round", type=int, default=25000)
    parser.add_argument("--mnli-train-limit", type=int, default=100000)
    parser.add_argument("--snli-limit", type=int, default=50000)
    args = parser.parse_args()

    dataset_cache = _configure_project_local_cache(ROOT)
    cache_kwargs = {
        "cache_dir": str(dataset_cache),
        "download_mode": "reuse_dataset_if_exists",
    }
    output_dir = ensure_dir(args.output_dir)
    train_rows = []
    validation_rows = []
    test_rows = []

    # FEVER in this cached config lacks direct evidence text, so stage 1 uses the public datasets
    # with usable claim/evidence text pairs directly available in cache.
    vitaminc = load_dataset("tals/vitaminc", **cache_kwargs)
    vitaminc_map = {
        "SUPPORTS": "SUPPORT",
        "REFUTES": "REFUTE",
        "NOT ENOUGH INFO": "NEUTRAL",
    }
    _append_rows(train_rows, vitaminc["train"], "vitaminc_train", lambda row: vitaminc_map.get(str(row.get("label"))), "claim", "evidence", "hf:vitaminc", limit=args.vitaminc_train_limit)
    _append_rows(validation_rows, vitaminc["validation"], "vitaminc_val", lambda row: vitaminc_map.get(str(row.get("label"))), "claim", "evidence", "hf:vitaminc")
    _append_rows(test_rows, vitaminc["test"], "vitaminc_test", lambda row: vitaminc_map.get(str(row.get("label"))), "claim", "evidence", "hf:vitaminc")

    nli_map = {0: "SUPPORT", 1: "NEUTRAL", 2: "REFUTE", "0": "SUPPORT", "1": "NEUTRAL", "2": "REFUTE"}
    anli = load_dataset("facebook/anli", "plain_text", **cache_kwargs)
    for split_name in ("train_r1", "train_r2", "train_r3"):
        _append_rows(train_rows, anli[split_name], split_name, lambda row: nli_map.get(row.get("label")), "hypothesis", "premise", "hf:anli", limit=args.anli_train_limit_per_round)
    for split_name in ("dev_r1", "dev_r2", "dev_r3"):
        _append_rows(validation_rows, anli[split_name], split_name, lambda row: nli_map.get(row.get("label")), "hypothesis", "premise", "hf:anli")
    for split_name in ("test_r1", "test_r2", "test_r3"):
        _append_rows(test_rows, anli[split_name], split_name, lambda row: nli_map.get(row.get("label")), "hypothesis", "premise", "hf:anli")

    mnli = load_dataset("nyu-mll/glue", "mnli", **cache_kwargs)
    _append_rows(train_rows, mnli["train"], "mnli_train", lambda row: nli_map.get(row.get("label")), "hypothesis", "premise", "hf:mnli", limit=args.mnli_train_limit)
    _append_rows(validation_rows, mnli["validation_matched"], "mnli_val", lambda row: nli_map.get(row.get("label")), "hypothesis", "premise", "hf:mnli")
    _append_rows(test_rows, mnli["test_matched"], "mnli_test", lambda row: nli_map.get(row.get("label")), "hypothesis", "premise", "hf:mnli")

    snli = load_dataset("stanfordnlp/snli", "plain_text", **cache_kwargs)
    snli_train = snli["train"].select(range(min(args.snli_limit, len(snli["train"]))))
    _append_rows(train_rows, snli_train, "snli_train", lambda row: nli_map.get(row.get("label")), "hypothesis", "premise", "hf:snli")
    _append_rows(validation_rows, snli["validation"], "snli_val", lambda row: nli_map.get(row.get("label")), "hypothesis", "premise", "hf:snli")
    _append_rows(test_rows, snli["test"], "snli_test", lambda row: nli_map.get(row.get("label")), "hypothesis", "premise", "hf:snli")

    _write_jsonl(output_dir / "train.jsonl", train_rows)
    _write_jsonl(output_dir / "validation.jsonl", validation_rows)
    _write_jsonl(output_dir / "test.jsonl", test_rows)
    metadata = {
        "train_rows": len(train_rows),
        "validation_rows": len(validation_rows),
        "test_rows": len(test_rows),
        "sources": ["vitaminc", "anli", "mnli", "snli"],
        "vitaminc_train_limit": int(args.vitaminc_train_limit),
        "anli_train_limit_per_round": int(args.anli_train_limit_per_round),
        "mnli_train_limit": int(args.mnli_train_limit),
        "snli_limit": int(args.snli_limit),
        "note": "FEVER cache in this repo does not include direct evidence text, so it is excluded from stage-1 supervised pairs.",
    }
    (output_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
