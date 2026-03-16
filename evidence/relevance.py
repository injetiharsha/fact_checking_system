import threading
import re
import json
import subprocess
import sys
import os
from contextlib import contextmanager
from pathlib import Path

import torch
import torch.nn.functional as F
from sentence_transformers import SentenceTransformer, util
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from training.common.config import runtime_model_settings
from evidence.bge_reranker import BGEReranker


@contextmanager
def _offline_hf():
    previous_hf = os.getenv("HF_HUB_OFFLINE")
    previous_tf = os.getenv("TRANSFORMERS_OFFLINE")
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    try:
        yield
    finally:
        if previous_hf is None:
            os.environ.pop("HF_HUB_OFFLINE", None)
        else:
            os.environ["HF_HUB_OFFLINE"] = previous_hf
        if previous_tf is None:
            os.environ.pop("TRANSFORMERS_OFFLINE", None)
        else:
            os.environ["TRANSFORMERS_OFFLINE"] = previous_tf


def _normalize_token(token):
    token = (token or "").lower().strip(".,;:!?()[]{}\"'")
    if token.endswith("ies") and len(token) > 4:
        return token[:-3] + "y"
    if token.endswith("es") and len(token) > 4:
        return token[:-2]
    if token.endswith("s") and len(token) > 3:
        return token[:-1]
    return token


def _token_set(text):
    return {
        _normalize_token(token)
        for token in re.findall(r"[A-Za-z0-9']+", text or "")
        if _normalize_token(token)
    }


def _model_cached(model_name):
    candidate_roots = []
    if os.getenv("MODEL_CACHE_DIR"):
        candidate_roots.append(Path(os.getenv("MODEL_CACHE_DIR")))
    if os.getenv("TRANSFORMERS_CACHE"):
        candidate_roots.append(Path(os.getenv("TRANSFORMERS_CACHE")))
    candidate_roots.append(Path(__file__).resolve().parents[1] / ".venv" / "model_cache")
    model_dir = model_name.replace("/", "--")
    for root in candidate_roots:
        if (root / f"models--{model_dir}").exists():
            return True
        if (root / "transformers" / f"models--{model_dir}").exists():
            return True
        if (root / "sentence_transformers" / f"models--{model_dir}").exists():
            return True
    return False


def _resolve_model_path(model_name):
    candidate_roots = []
    if os.getenv("MODEL_CACHE_DIR"):
        candidate_roots.append(Path(os.getenv("MODEL_CACHE_DIR")))
    if os.getenv("TRANSFORMERS_CACHE"):
        candidate_roots.append(Path(os.getenv("TRANSFORMERS_CACHE")))
    candidate_roots.append(Path(__file__).resolve().parents[1] / ".venv" / "model_cache")
    model_dir = model_name.replace("/", "--")
    relative_candidates = [
        Path("sentence_transformers") / f"models--{model_dir}",
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


class RelevanceScorer:
    def __init__(self):
        self._lock = threading.Lock()
        self._score_cache = {}
        self._semantic_cache = {}
        self.provider_name = "current"
        runtime = runtime_model_settings("relevance")
        requested_device = runtime.get("device")
        if requested_device:
            selected_device = requested_device
        else:
            selected_device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = torch.device(selected_device)
        self.embed_device = os.getenv(
            "RELEVANCE_EMBED_DEVICE",
            "cuda" if torch.cuda.is_available() else "cpu",
        ).strip().lower()
        self.rerank_device = (
            os.getenv("BGE_RERANKER_DEVICE")
            or os.getenv("RELEVANCE_RERANK_DEVICE")
            or "cpu"
        ).strip().lower()
        self.model = None
        self.tokenizer = None
        self.model_type = None
        self.trained_checkpoint = None
        self.trained_device = requested_device or "cpu"
        self.helper_script = Path(__file__).with_name("relevance_subprocess_infer.py")
        self.reranker_provider = (os.getenv("RERANKER_PROVIDER") or "current").strip().lower()
        self.bge_reranker = None

        checkpoint = runtime.get("checkpoint")
        if runtime.get("enabled") and checkpoint is not None:
            self.trained_checkpoint = Path(checkpoint)
            print(
                "Configured trained relevance checkpoint for isolated inference:",
                self.trained_checkpoint,
            )

        for model_name in ("BAAI/bge-small-en-v1.5", "all-MiniLM-L6-v2"):
            if not _model_cached(model_name) and not _model_cached(f"sentence-transformers/{model_name}"):
                continue
            try:
                local_path = _resolve_model_path(model_name) or _resolve_model_path(f"sentence-transformers/{model_name}")
                model_ref = str(local_path) if local_path is not None else model_name
                with _offline_hf():
                    self.model = SentenceTransformer(model_ref, device=self.embed_device)
                self.model_type = "bi_encoder"
                print(
                    f"RelevanceScorer using cached model: {model_name} "
                    f"on semantic device {self.embed_device}"
                )
                break
            except Exception:
                continue

        if self.reranker_provider == "bge":
            self.bge_reranker = BGEReranker(device=self.rerank_device)
            if self.bge_reranker.available:
                self.provider_name = "bge"
            else:
                self.bge_reranker = None

        if self.model is None:
            print("RelevanceScorer fallback: lexical overlap mode")

    @property
    def has_trained_reranker(self):
        return self.trained_checkpoint is not None

    @property
    def has_semantic_ranker(self):
        return self.model_type == "bi_encoder" and self.model is not None

    def fast_score(self, claim, text):
        claim_words = _token_set(claim)
        text_words = _token_set(text)
        if not claim_words:
            return 0.0
        return round(len(claim_words & text_words) / len(claim_words), 3)

    def semantic_score(self, claim, text):
        if not text:
            return 0.0
        cache_key = (
            " ".join((claim or "").strip().lower().split()),
            " ".join((text or "").strip().lower().split()),
        )
        cached = self._semantic_cache.get(cache_key)
        if cached is not None:
            return cached
        if not self.has_semantic_ranker:
            score = self.fast_score(claim, text)
            self._semantic_cache[cache_key] = score
            return score

        claim_emb = self.model.encode(claim, convert_to_tensor=True)
        text_emb = self.model.encode(text, convert_to_tensor=True)
        score = util.cos_sim(claim_emb, text_emb)[0][0].item()
        rounded = round(float(score), 3)
        self._semantic_cache[cache_key] = rounded
        return rounded

    def score(self, claim, text):
        if not text:
            return 0
        cache_key = (
            " ".join((claim or "").strip().lower().split()),
            " ".join((text or "").strip().lower().split()),
        )
        cached = self._score_cache.get(cache_key)
        if cached is not None:
            return cached

        if self.bge_reranker is not None:
            bge_score = self.bge_reranker.score(claim, text)
            if bge_score is not None:
                self._score_cache[cache_key] = bge_score
                return bge_score

        if self.trained_checkpoint is not None:
            trained_score = self._score_with_subprocess(claim, text)
            if trained_score is not None:
                self._score_cache[cache_key] = trained_score
                return trained_score

        if self.model_type == "cross_encoder" and self.model is not None and self.tokenizer is not None:
            inputs = self.tokenizer(
                claim,
                text,
                return_tensors="pt",
                truncation=True,
                padding=True,
                max_length=256,
            ).to(self.device)
            with self._lock:
                with torch.no_grad():
                    outputs = self.model(**inputs)
                    logits = outputs.logits
            if logits.shape[-1] == 1:
                score = torch.sigmoid(logits[0][0]).item()
            else:
                score = F.softmax(logits, dim=-1)[0][-1].item()
            rounded = round(float(score), 3)
            self._score_cache[cache_key] = rounded
            return rounded

        if self.model is None:
            score = self.fast_score(claim, text)
            self._score_cache[cache_key] = score
            return score

        score = self.semantic_score(claim, text)
        self._score_cache[cache_key] = score
        return score

    def rerank(self, claim, texts):
        rows = []
        for text in texts:
            rows.append({
                "text": text,
                "score": self.score(claim, text),
                "provider": self.provider_name,
            })
        rows.sort(key=lambda item: float(item.get("score", 0.0)), reverse=True)
        return rows

    def _score_with_subprocess(self, claim, text):
        if not self.helper_script.exists():
            return None

        command = [
            sys.executable,
            str(self.helper_script),
            "--checkpoint",
            str(self.trained_checkpoint),
            "--device",
            self.trained_device,
            "--claim",
            claim,
            "--text",
            text,
        ]

        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=45,
                check=False,
            )
        except Exception as exc:
            print(f"Trained relevance subprocess failed to start: {exc}")
            return None

        if completed.returncode != 0:
            stderr = (completed.stderr or "").strip()
            if stderr:
                print(f"Trained relevance subprocess failed: {stderr[:300]}")
            return None

        stdout = (completed.stdout or "").strip().splitlines()
        if not stdout:
            return None

        try:
            payload = json.loads(stdout[-1])
        except Exception as exc:
            print(f"Invalid trained relevance subprocess output: {exc}")
            return None

        score = payload.get("score")
        if score is None:
            return None
        return round(float(score), 3)
