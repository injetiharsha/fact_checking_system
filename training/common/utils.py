import json
import os
import random
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable

import numpy as np
import torch


def ensure_dir(path: str | Path) -> Path:
    out = Path(path)
    out.mkdir(parents=True, exist_ok=True)
    return out


def read_json(path: str | Path) -> Dict[str, Any]:
    with Path(path).open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def write_json(path: str | Path, payload: Dict[str, Any]) -> None:
    with Path(path).open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def get_device() -> torch.device:
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def current_commit(default: str = "unknown") -> str:
    return os.getenv("GIT_COMMIT", default)


def stratified_split_records(
    records: list[Dict[str, Any]],
    label_key: str,
    validation_ratio: float = 0.1,
    test_ratio: float = 0.1,
    seed: int = 42,
) -> tuple[list[Dict[str, Any]], list[Dict[str, Any]], list[Dict[str, Any]]]:
    if len(records) < 3:
        return records, [], []

    rng = random.Random(seed)
    by_label: dict[str, list[Dict[str, Any]]] = defaultdict(list)
    for record in records:
        by_label[str(record[label_key])].append(record)

    train_rows: list[Dict[str, Any]] = []
    validation_rows: list[Dict[str, Any]] = []
    test_rows: list[Dict[str, Any]] = []

    for label_rows in by_label.values():
        bucket = list(label_rows)
        rng.shuffle(bucket)
        count = len(bucket)

        if count == 1:
            train_rows.extend(bucket)
            continue
        if count == 2:
            validation_rows.append(bucket[0])
            train_rows.append(bucket[1])
            continue

        val_count = max(1, int(round(count * validation_ratio)))
        test_count = max(1, int(round(count * test_ratio)))

        if val_count + test_count >= count:
            if count >= 3:
                val_count = 1
                test_count = 1
            else:
                val_count = 1
                test_count = 0

        validation_rows.extend(bucket[:val_count])
        test_rows.extend(bucket[val_count:val_count + test_count])
        train_rows.extend(bucket[val_count + test_count:])

    return train_rows, validation_rows, test_rows
