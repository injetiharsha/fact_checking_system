from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable

from sklearn.metrics import accuracy_score, precision_recall_fscore_support

from training.common.utils import current_commit, ensure_dir, write_json


def classification_metrics(y_true: Iterable[int], y_pred: Iterable[int]) -> Dict[str, Any]:
    precision, recall, f1, _ = precision_recall_fscore_support(
        list(y_true),
        list(y_pred),
        average="weighted",
        zero_division=0,
    )
    return {
        "accuracy": round(float(accuracy_score(list(y_true), list(y_pred))), 4),
        "precision_weighted": round(float(precision), 4),
        "recall_weighted": round(float(recall), 4),
        "f1_weighted": round(float(f1), 4),
    }


def save_run_metrics(output_dir: str | Path, task: str, metrics: Dict[str, Any], extra: Dict[str, Any] | None = None) -> Path:
    target_dir = ensure_dir(output_dir)
    payload = {
        "task": task,
        "metrics": metrics,
        "git_commit": current_commit(),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    if extra:
        payload.update(extra)
    path = target_dir / f"{task}_metrics.json"
    write_json(path, payload)
    return path
