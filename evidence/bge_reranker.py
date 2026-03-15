import threading
import os
from pathlib import Path

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer


def _resolve_model_path(model_name):
    candidate_roots = []
    if os.getenv("MODEL_CACHE_DIR"):
        candidate_roots.append(Path(os.getenv("MODEL_CACHE_DIR")))
    if os.getenv("TRANSFORMERS_CACHE"):
        candidate_roots.append(Path(os.getenv("TRANSFORMERS_CACHE")))
    candidate_roots.append(Path(__file__).resolve().parents[1] / ".venv" / "model_cache")
    model_dir = model_name.replace("/", "--")
    relative_candidates = [
        Path("transformers") / f"models--{model_dir}",
        Path(f"models--{model_dir}"),
    ]
    for root in candidate_roots:
        for relative in relative_candidates:
            model_root = root / relative
            refs_main = model_root / "refs" / "main"
            snapshots_dir = model_root / "snapshots"
            if refs_main.exists():
                revision = refs_main.read_text(encoding="utf-8").strip()
                snapshot = snapshots_dir / revision
                if snapshot.exists():
                    return snapshot
            if snapshots_dir.exists():
                snapshots = sorted([path for path in snapshots_dir.iterdir() if path.is_dir()])
                if snapshots:
                    return snapshots[-1]
    return None


class BGEReranker:
    def __init__(self, model_name="BAAI/bge-reranker-base", device=None):
        self.model_name = model_name
        selected_device = (
            device
            or os.getenv("BGE_RERANKER_DEVICE")
            or os.getenv("RELEVANCE_RERANK_DEVICE")
            or "cpu"
        )
        self.device = torch.device(selected_device)
        self.tokenizer = None
        self.model = None
        self.available = False
        self._lock = threading.Lock()
        try:
            local_path = _resolve_model_path(model_name)
            model_ref = str(local_path) if local_path is not None else model_name
            self.tokenizer = AutoTokenizer.from_pretrained(model_ref, local_files_only=True)
            self.model = AutoModelForSequenceClassification.from_pretrained(model_ref, local_files_only=True)
            self.model.to(self.device)
            self.model.eval()
            self.available = True
            print(f"BGEReranker using cached model: {model_name} on {self.device}")
        except Exception as exc:
            print(f"BGEReranker unavailable, falling back: {exc}")

    def score(self, claim, text):
        if not self.available or not text:
            return None
        encoded = self.tokenizer(
            claim,
            text,
            return_tensors="pt",
            truncation=True,
            padding=True,
            max_length=512,
        )
        encoded = {k: v.to(self.device) for k, v in encoded.items()}
        with self._lock:
            with torch.no_grad():
                logits = self.model(**encoded).logits
        score = torch.sigmoid(logits[0][0]).item()
        return round(float(score), 3)
