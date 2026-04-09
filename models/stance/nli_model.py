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


def _sanitize_ipc_text(text, max_chars=1200):
    value = (text or "").replace("\x00", "")
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    value = "".join(
        ch for ch in value
        if ch == "\n" or ch == "\t" or ord(ch) >= 32
    )
    value = " ".join(value.split())
    return value[:max_chars]


class NLIModel:
    def _print_device_once(self):
        if not hasattr(self, "_device_printed"):
            print(f"[NLIModel] Device in use for claim analysis: {self.device} (CUDA available: {torch.cuda.is_available()})")
            self._device_printed = True
            self.TRAINED_CONFIDENCE_THRESHOLD = 0.58

    def __init__(self):
        self._lock = threading.Lock()
        self._worker = None
        self._worker_lock = threading.Lock()
        self._worker_ready = False
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
            if self.trained_checkpoint is not None:
                print(
                    "NLIModel foundation cache unavailable; using trained subprocess path with heuristic fallback"
                )
            else:
                print("NLIModel fallback: heuristic mode (no cached model)")

    def _start_worker(self):
        if self._worker_ready and self._worker is not None and self._worker.poll() is None:
            return True
        if self.trained_checkpoint is None or not self.helper_script.exists():
            return False

        command = [
            sys.executable,
            str(self.helper_script),
            "--checkpoint",
            str(self.trained_checkpoint),
            "--device",
            self.trained_device,
            "--claim",
            "__serve__",
            "--evidence",
            "__serve__",
            "--serve",
        ]

        try:
            self._worker = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                bufsize=1,
            )
        except Exception as exc:
            print(f"Failed to start trained NLI worker: {exc}")
            self._worker = None
            self._worker_ready = False
            return False

        try:
            ready_line = self._worker.stdout.readline().strip() if self._worker.stdout else ""
            payload = json.loads(ready_line) if ready_line else {}
            if payload.get("status") == "ready":
                self._worker_ready = True
                print(
                    "NLIModel using persistent stance worker:",
                    self.trained_checkpoint,
                    "on",
                    self.trained_device,
                )
                return True
        except Exception as exc:
            print(f"Stance worker failed to initialize: {exc}")

        self._stop_worker()
        return False

    def _stop_worker(self):
        worker = self._worker
        self._worker = None
        self._worker_ready = False
        if worker is None:
            return
        try:
            if worker.stdin:
                worker.stdin.write(json.dumps({"command": "shutdown"}) + "\n")
                worker.stdin.flush()
        except Exception:
            pass
        try:
            if worker.stdin:
                worker.stdin.close()
        except Exception:
            pass
        try:
            worker.terminate()
            worker.wait(timeout=2)
        except Exception:
            try:
                worker.kill()
            except Exception:
                pass

    def predict(self, claim, evidence):
        self._print_device_once()
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
            if trained_result is not None:
                _, trained_conf = trained_result
                if float(trained_conf) < self.TRAINED_CONFIDENCE_THRESHOLD:
                    trained_result = None

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

    def predict_many(self, claim, evidences, batch_size=16):
        self._print_device_once()
        if not evidences:
            return []

        outputs = [None] * len(evidences)
        missing = []
        for index, evidence in enumerate(evidences):
            cache_key = (
                " ".join((claim or "").strip().lower().split()),
                " ".join((evidence or "").strip().lower().split()),
            )
            cached = self._prediction_cache.get(cache_key)
            if cached is not None:
                outputs[index] = cached
            else:
                missing.append((index, evidence, cache_key))

        # Split into batches to avoid OOM
        def batcher(seq, size):
            for pos in range(0, len(seq), size):
                yield seq[pos:pos+size]

        def run_batch(batch_claim, batch_evidences):
            try:
                return self._predict_with_cached_model_many(batch_claim, batch_evidences)
            except RuntimeError as e:
                if "out of memory" in str(e).lower() and self.device.type == "cuda":
                    print("[NLIModel] CUDA OOM, retrying on CPU...")
                    torch.cuda.empty_cache()
                    self.device = torch.device("cpu")
                    self.model.to(self.device)
                    return self._predict_with_cached_model_many(batch_claim, batch_evidences)
                else:
                    raise

        # Helper for batch prediction
        def _predict_with_cached_model_many(claim, evidences):
            inputs = self.tokenizer(
                [claim] * len(evidences),
                evidences,
                return_tensors="pt",
                truncation=True,
                padding=True,
            ).to(self.device)
            with torch.no_grad():
                outputs = self.model(**inputs)
                probs = F.softmax(outputs.logits, dim=1)
                predicted = torch.argmax(probs, dim=1).tolist()
                confidences = probs.max(dim=1).values.tolist()
                labels = [self.model.config.id2label.get(idx, f"LABEL_{idx}") for idx in predicted]
                return list(zip(labels, confidences))

        self._predict_with_cached_model_many = _predict_with_cached_model_many

        if missing and self.model is not None and self.tokenizer is not None:
            for batch in batcher(missing, batch_size):
                batch_indices = [item[0] for item in batch]
                batch_evidences = [item[1] for item in batch]
                batch_keys = [item[2] for item in batch]
                batch_results = run_batch(claim, batch_evidences)
                for idx, result, key in zip(batch_indices, batch_results, batch_keys):
                    self._prediction_cache[key] = result
                    outputs[idx] = result

        # Fallback for missing predictions
        for index, evidence in enumerate(evidences):
            if outputs[index] is None:
                outputs[index] = self.predict(claim, evidence)

        return outputs

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
        predictions = self._predict_many_with_worker(claim, [evidence])
        if not predictions:
            return None
        return predictions[0]

    def _predict_many_with_worker(self, claim, evidences, allow_retry=True):
        if not evidences:
            return []
        with self._worker_lock:
            if not self._start_worker():
                return None
            try:
                if not self._worker or not self._worker.stdin or not self._worker.stdout:
                    return None
                safe_claim = _sanitize_ipc_text(claim, max_chars=512)
                payload = {
                    "items": [
                        {
                            "claim": safe_claim,
                            "evidence": _sanitize_ipc_text(evidence, max_chars=1000),
                        }
                        for evidence in evidences
                    ]
                }
                serialized = json.dumps(payload, ensure_ascii=True, separators=(",", ":"))
                self._worker.stdin.write(serialized + "\n")
                self._worker.stdin.flush()
                result_line = self._worker.stdout.readline().strip()
                if not result_line:
                    return None
                payload = json.loads(result_line)
                predictions = payload.get("predictions")
                if not isinstance(predictions, list):
                    return None
                self.model_name = f"trained_subprocess:{self.trained_checkpoint}"
                return [
                    (row.get("label"), float(row.get("confidence")))
                    for row in predictions
                    if row.get("label") is not None and row.get("confidence") is not None
                ]
            except Exception as exc:
                print(f"Trained NLI worker request failed: {exc}")
                self._stop_worker()
                if allow_retry:
                    return self._predict_many_with_worker(claim, evidences, allow_retry=False)
                return None
