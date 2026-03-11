import re

import torch
import torch.nn.functional as F
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from training.common.config import runtime_model_settings


class NLIModel:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print("Using device:", self.device)

        self.model = None
        self.tokenizer = None
        self.model_name = None

        runtime = runtime_model_settings("stance")
        checkpoint = runtime.get("checkpoint")
        if runtime.get("enabled") and checkpoint is not None:
            try:
                print(f"Loading trained NLI checkpoint: {checkpoint}")
                self.tokenizer = AutoTokenizer.from_pretrained(str(checkpoint))
                self.model = AutoModelForSequenceClassification.from_pretrained(
                    str(checkpoint)
                ).to(self.device)
                self.model_name = str(checkpoint)
                print(f"Loaded trained NLI checkpoint: {checkpoint}")
                return
            except Exception as exc:
                print(f"Trained NLI checkpoint load failed: {exc}")

        candidates = [
            "cross-encoder/nli-deberta-v3-small",
            "ynie/roberta-large-snli_mnli_fever_anli_R1_R2_R3-nli",
        ]

        for model_name in candidates:
            try:
                print(f"Loading NLI model from cache: {model_name}")
                self.tokenizer = AutoTokenizer.from_pretrained(
                    model_name, local_files_only=True
                )
                self.model = AutoModelForSequenceClassification.from_pretrained(
                    model_name, local_files_only=True
                ).to(self.device)
                self.model_name = model_name
                print(f"Loaded cached NLI model: {model_name}")
                break
            except Exception:
                continue

        if self.model is None:
            print("NLIModel fallback: heuristic mode (no cached model)")

    def predict(self, claim, evidence):
        if self.model is None or self.tokenizer is None:
            claim_text = (claim or "").lower()
            text = (evidence or "").lower()
            claim_words = set(re.findall(r"[a-z0-9]+", claim_text))
            evidence_words = set(re.findall(r"[a-z0-9]+", text))

            if not claim_words:
                return "NEUTRAL", 0.5

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
                return "REFUTE", 0.75
            if key_overlap >= 0.3 and any(c in text for c in refute_cues):
                return "REFUTE", 0.62
            if key_overlap >= 0.72 and not any(c in text for c in support_blockers):
                return "SUPPORT", 0.59

            return "NEUTRAL", 0.5

        inputs = self.tokenizer(
            claim,
            evidence,
            return_tensors="pt",
            truncation=True,
            padding=True,
        ).to(self.device)

        with torch.no_grad():
            outputs = self.model(**inputs)
            probs = F.softmax(outputs.logits, dim=1)

        predicted = torch.argmax(probs, dim=1).item()
        confidence = probs[0][predicted].item()
        label = self.model.config.id2label.get(predicted, f"LABEL_{predicted}")
        return label, confidence
