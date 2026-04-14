import os
from dotenv import load_dotenv
from pathlib import Path
from typing import Any, Dict

try:
    import yaml
except Exception:  # pragma: no cover - import guard for environments without PyYAML
    yaml = None


ROOT_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT_DIR / '.env'
load_dotenv(ENV_PATH, override=True)

RUNTIME_ENV_MAP = {
    "claim_checkability": {
        "enabled": "ENABLE_TRAINED_CLAIM_CHECKABILITY",
        "checkpoint": "CLAIM_CHECKABILITY_CHECKPOINT",
        "device": "CLAIM_CHECKABILITY_DEVICE",
    },
    "claim_type": {
        "enabled": "ENABLE_TRAINED_CLAIM_TYPE",
        "checkpoint": "CLAIM_TYPE_CHECKPOINT",
        "device": "CLAIM_TYPE_DEVICE",
    },
    "context": {
        "enabled": "ENABLE_TRAINED_CONTEXT",
        "checkpoint": "CONTEXT_CHECKPOINT",
        "device": "CONTEXT_DEVICE",
    },
    "stance": {
        "enabled": "ENABLE_TRAINED_STANCE",
        "checkpoint": "STANCE_CHECKPOINT",
        "device": "STANCE_DEVICE",
    },
    "relevance": {
        "enabled": "ENABLE_TRAINED_RELEVANCE",
        "checkpoint": "RELEVANCE_CHECKPOINT",
        "device": "RELEVANCE_DEVICE",
    },
}


def load_yaml_config(path: str | Path) -> Dict[str, Any]:
    if yaml is None:
        raise RuntimeError("PyYAML is required to load training configs.")
    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def feature_enabled(task: str, default: bool = False) -> bool:
    env_name = RUNTIME_ENV_MAP[task]["enabled"]
    value = os.getenv(env_name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def checkpoint_path(task: str) -> Path | None:
    env_name = RUNTIME_ENV_MAP[task]["checkpoint"]
    value = os.getenv(env_name)
    if not value:
        return None
    path = Path(value).expanduser()
    if path.exists():
        return path
    print(f"WARNING: configured {task} checkpoint does not exist: {path}")
    return None


def runtime_device(task: str, default: str | None = None) -> str | None:
    env_name = RUNTIME_ENV_MAP[task].get("device")
    value = os.getenv(env_name) if env_name else None
    if value:
        return value.strip().lower()
    return default


def runtime_model_settings(task: str) -> Dict[str, Any]:
    return {
        "enabled": feature_enabled(task),
        "checkpoint": checkpoint_path(task),
        "device": runtime_device(task),
    }
