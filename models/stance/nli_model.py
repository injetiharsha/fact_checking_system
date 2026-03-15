import re
import threading
import json
import subprocess
import sys
import os
from pathlib import Path

import torch
import torch.nn.functional as F
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from training.common.config import runtime_model_settings


def _resolve_model_path(model_name):
    candidate_roots = []
    if os.getenv("MODEL_CACHE_DIR"):
        candidate_roots.append(Path(os.getenv("MODEL_CACHE_DIR")))
    if os.getenv("TRANSFORMERS_CACHE"):
        candidate_roots.append(Path(os.getenv("TRANSFORMERS_CACHE")))
    candidate_roots.append(Path(__file__).resolve().parents[2] / ".venv" / "model_cache")
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


def _is_windows_unsafe_model(model_name):
    if os.name != "nt":
        return False
    if os.getenv("ALLOW_WINDOWS_SENTENCEPIECE_MODELS", "0") == "1":
        return False
    lowered = (model_name or "").lower()
    return "deberta" in lowered


class NLIModel:
    def __init__(self):
        self._lock = threading.Lock()
        self._prediction_cache = {}
        runtime = runtime_model_settings("stance")
        requested_device = runtime.get("device")
        foundation_device = (os.getenv("STANCE_FOUNDATION_DEVICE") or "").strip().lower()
        if requested_device:
            selected_device = requested_device
        else:
            selected_device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = torch.device(foundation_device or selected_device)
        print("Using device:", self.device)

        self.model = None
        self.tokenizer = None
        self.model_name = None
        self.trained_checkpoint = None
        self.trained_device = requested_device or "cpu"
        self.helper_script = Path(__file__).with_name("subprocess_infer.py")

        checkpoint = runtime.get("checkpoint")
        if runtime.get("enabled") and checkpoint is not None:
            self.trained_checkpoint = Path(checkpoint)
            print(
                "Configured trained NLI checkpoint for isolated inference:",
                self.trained_checkpoint,
            )

        preferred_foundation = (
            os.getenv("STANCE_FOUNDATION_MODEL")
            or os.getenv("VERIFIER_FOUNDATION_MODEL")
            or ""
        ).strip()
        candidates = []
        if preferred_foundation:
            candidates.append(preferred_foundation)
        candidates.extend([
            "ynie/roberta-large-snli_mnli_fever_anli_R1_R2_R3-nli",
            "cross-encoder/nli-deberta-v3-small",
        ])

        for model_name in candidates:
            if _is_windows_unsafe_model(model_name):
                print(f"Skipping Windows-unsafe NLI model: {model_name}")
                continue
            try:
                print(f"Loading NLI model from cache: {model_name}")
                local_path = _resolve_model_path(model_name)
                model_ref = str(local_path) if local_path is not None else model_name
                self.tokenizer = AutoTokenizer.from_pretrained(
                    model_ref, local_files_only=True, use_fast=False
                )
                self.model = AutoModelForSequenceClassification.from_pretrained(
                    model_ref, local_files_only=True
                ).to(self.device)
                self.model.eval()
                self.model_name = model_name
                print(f"Loaded cached NLI model: {model_name}")
                break
            except Exception:
                continue

        if self.model is None:
            print("NLIModel fallback: heuristic mode (no cached model)")

    def predict(self, claim, evidence):
        cache_key = (
            " ".join((claim or "").strip().lower().split()),
            " ".join((evidence or "").strip().lower().split()),
        )
        cached = self._prediction_cache.get(cache_key)
        if cached is not None:
            return cached

        trained_result = None
        if self.trained_checkpoint is not None:
            trained_result = self._predict_with_subprocess(claim, evidence)

        foundation_result = None
        if self.model is not None and self.tokenizer is not None:
            foundation_result = self._predict_with_cached_model(claim, evidence)

        combined = self._combine_predictions(trained_result, foundation_result)
        if combined is not None:
            self._prediction_cache[cache_key] = combined
            return combined

        if self.model is None or self.tokenizer is None:
            claim_text = (claim or "").lower()
            text = (evidence or "").lower()
            claim_words = set(re.findall(r"[a-z0-9]+", claim_text))
            evidence_words = set(re.findall(r"[a-z0-9]+", text))

            if not claim_words:
                result = ("NEUTRAL", 0.5)
                self._prediction_cache[cache_key] = result
                return result

            overlap = len(claim_words & evidence_words) / max(len(claim_words), 1)
            stop = {
                "the", "and", "for", "with", "from", "that", "this", "there", "their",
                "have", "has", "had", "are", "was", "were", "can", "could", "will",
                "would", "about", "into", "than", "over", "under", "your", "our",
            }
            claim_key = {w for w in claim_words if len(w) > 3 and w not in stop}
            key_overlap = (
                len(claim_key & evidence_words) / max(len(claim_key), 1)
                if claim_key else overlap
            )

            refute_cues = (
                "hoax", "fake", "myth", "false", "debunk", "does not", "doesn't",
                "cannot", "can't", "no evidence", "not true", "incorrect", "misleading"
            )
            support_blockers = (
                "whether", "might", "maybe", "could", "question", "rumor", "alleged",
                "conspiracy theory", "is it true", "?"
            )
            shape_refute = (
                ("flat" in claim_words and any(t in evidence_words for t in {"sphere", "spherical", "round", "globe"}))
                or ("round" in claim_words and "flat" in evidence_words)
                or ("spherical" in claim_words and "flat" in evidence_words)
            )

            if shape_refute:
                result = ("REFUTE", 0.75)
                self._prediction_cache[cache_key] = result
                return result
            if key_overlap >= 0.3 and any(c in text for c in refute_cues):
                result = ("REFUTE", 0.62)
                self._prediction_cache[cache_key] = result
                return result
            if key_overlap >= 0.72 and not any(c in text for c in support_blockers):
                result = ("SUPPORT", 0.59)
                self._prediction_cache[cache_key] = result
                return result

            result = ("NEUTRAL", 0.5)
            self._prediction_cache[cache_key] = result
            return result

        inputs = self.tokenizer(
            claim,
            evidence,
            return_tensors="pt",
            truncation=True,
            padding=True,
        ).to(self.device)

        with self._lock:
            with torch.no_grad():
                outputs = self.model(**inputs)
                probs = F.softmax(outputs.logits, dim=1)

        predicted = torch.argmax(probs, dim=1).item()
        confidence = probs[0][predicted].item()
        label = self.model.config.id2label.get(predicted, f"LABEL_{predicted}")
        result = (label, confidence)
        self._prediction_cache[cache_key] = result
        return result

    def _predict_with_cached_model(self, claim, evidence):
        inputs = self.tokenizer(
            claim,
            evidence,
            return_tensors="pt",
            truncation=True,
            padding=True,
        ).to(self.device)

        with self._lock:
            with torch.no_grad():
                outputs = self.model(**inputs)
                probs = F.softmax(outputs.logits, dim=1)

        predicted = torch.argmax(probs, dim=1).item()
        confidence = probs[0][predicted].item()
        label = self.model.config.id2label.get(predicted, f"LABEL_{predicted}")
        return label, confidence

    def _combine_predictions(self, trained_result, foundation_result):
        if trained_result is None and foundation_result is None:
            return None
        if trained_result is None:
            return foundation_result
        if foundation_result is None:
            return trained_result

        trained_label, trained_conf = trained_result
        foundation_label, foundation_conf = foundation_result

        trained_norm = self._normalize_label(trained_label)
        foundation_norm = self._normalize_label(foundation_label)

        if trained_norm == foundation_norm:
            return trained_label, max(float(trained_conf), float(foundation_conf))

        if trained_norm == "NEUTRAL" and foundation_norm != "NEUTRAL" and foundation_conf >= 0.58:
            return foundation_label, float(foundation_conf)

        if foundation_norm == "NEUTRAL" and trained_norm != "NEUTRAL" and trained_conf >= 0.58:
            return trained_label, float(trained_conf)

        if trained_norm != "NEUTRAL" and foundation_norm != "NEUTRAL":
            if abs(float(trained_conf) - float(foundation_conf)) >= 0.15:
                return (
                    (trained_label, float(trained_conf))
                    if float(trained_conf) > float(foundation_conf)
                    else (foundation_label, float(foundation_conf))
                )
            return "NEUTRAL", max(float(trained_conf), float(foundation_conf))

        return trained_result if float(trained_conf) >= float(foundation_conf) else foundation_result

    @staticmethod
    def _normalize_label(label):
        label = (label or "").upper()
        stance_map = {
            "ENTAILMENT": "SUPPORT",
            "CONTRADICTION": "REFUTE",
            "NEUTRAL": "NEUTRAL",
            "LABEL_0": "REFUTE",
            "LABEL_1": "NEUTRAL",
            "LABEL_2": "SUPPORT",
            "SUPPORT": "SUPPORT",
            "REFUTE": "REFUTE",
        }
        return stance_map.get(label, "NEUTRAL")

    def _predict_with_subprocess(self, claim, evidence):
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
            "--evidence",
            evidence,
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
            print(f"Trained NLI subprocess failed to start: {exc}")
            return None

        if completed.returncode != 0:
            stderr = (completed.stderr or "").strip()
            if stderr:
                print(f"Trained NLI subprocess failed: {stderr[:300]}")
            return None

        stdout = (completed.stdout or "").strip().splitlines()
        if not stdout:
            return None

        try:
            payload = json.loads(stdout[-1])
        except Exception as exc:
            print(f"Invalid trained NLI subprocess output: {exc}")
            return None

        label = payload.get("label")
        confidence = payload.get("confidence")
        if label is None or confidence is None:
            return None

        self.model_name = f"trained_subprocess:{self.trained_checkpoint}"
        return label, float(confidence)

