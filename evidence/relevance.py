import threading
import re
import json
import subprocess
import sys
from pathlib import Path

import torch
import torch.nn.functional as F
from sentence_transformers import SentenceTransformer, util
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from training.common.config import runtime_model_settings


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


class RelevanceScorer:
    def __init__(self):
        self._lock = threading.Lock()
        runtime = runtime_model_settings("relevance")
        requested_device = runtime.get("device")
        if requested_device:
            selected_device = requested_device
        else:
            selected_device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = torch.device(selected_device)
        self.model = None
        self.tokenizer = None
        self.model_type = None
        self.trained_checkpoint = None
        self.trained_device = requested_device or "cpu"
        self.helper_script = Path(__file__).with_name("relevance_subprocess_infer.py")

        checkpoint = runtime.get("checkpoint")
        if runtime.get("enabled") and checkpoint is not None:
            self.trained_checkpoint = Path(checkpoint)
            print(
                "Configured trained relevance checkpoint for isolated inference:",
                self.trained_checkpoint,
            )

        for model_name in ("BAAI/bge-small-en-v1.5", "all-MiniLM-L6-v2"):
            try:
                self.model = SentenceTransformer(model_name, local_files_only=True)
                self.model_type = "bi_encoder"
                print(f"RelevanceScorer using cached model: {model_name}")
                break
            except Exception:
                continue

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
        if not self.has_semantic_ranker:
            return self.fast_score(claim, text)

        claim_emb = self.model.encode(claim, convert_to_tensor=True)
        text_emb = self.model.encode(text, convert_to_tensor=True)
        score = util.cos_sim(claim_emb, text_emb)[0][0].item()
        return round(float(score), 3)

    def score(self, claim, text):
        if not text:
            return 0

        if self.trained_checkpoint is not None:
            trained_score = self._score_with_subprocess(claim, text)
            if trained_score is not None:
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
            return round(float(score), 3)

        if self.model is None:
            return self.fast_score(claim, text)

        return self.semantic_score(claim, text)

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
