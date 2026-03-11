import re
from enum import Enum

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from training.common.config import runtime_model_settings


class ClaimType(Enum):
    FACTUAL = "factual"
    OPINION = "opinion"
    MIXED = "mixed"
    NUMERICAL = "numerical"


class ClaimTypeClassifier:
    """Claim type classifier with offline-safe fallback."""

    MODEL_CONFIDENCE_THRESHOLD = 0.65
    MIXED_BAND = 0.15

    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = None
        self.model = None
        self.model_mode = "heuristic"

        runtime = runtime_model_settings("claim_type")
        checkpoint = runtime.get("checkpoint")
        if runtime.get("enabled") and checkpoint is not None:
            try:
                self.tokenizer = AutoTokenizer.from_pretrained(str(checkpoint))
                self.model = AutoModelForSequenceClassification.from_pretrained(
                    str(checkpoint)
                ).to(self.device)
                self.model.eval()
                self.model_mode = "trained_multiclass"
                print(f"ClaimTypeClassifier using trained checkpoint: {checkpoint}")
                return
            except Exception as exc:
                print(f"ClaimTypeClassifier checkpoint load failed: {exc}")

        candidates = [
            "distilbert-base-uncased-finetuned-sst-2-english",
            "distilbert-base-uncased",
        ]

        for model_name in candidates:
            try:
                self.tokenizer = AutoTokenizer.from_pretrained(
                    model_name, local_files_only=True
                )
                self.model = AutoModelForSequenceClassification.from_pretrained(
                    model_name, local_files_only=True
                ).to(self.device)
                self.model.eval()
                self.model_mode = "cached_binary"
                print(f"ClaimTypeClassifier using cached model: {model_name}")
                break
            except Exception:
                continue

        if self.model is None:
            print("ClaimTypeClassifier fallback: heuristic mode (no cached model)")

    def classify(self, claim: str) -> dict:
        if self.model is None or self.tokenizer is None:
            return self._heuristic_classify(
                claim,
                decision_source="heuristic_no_model",
            )

        inputs = self.tokenizer(
            claim,
            max_length=512,
            truncation=True,
            return_tensors="pt",
        ).to(self.device)

        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits
            probabilities = torch.nn.functional.softmax(logits, dim=-1)

        if probabilities.shape[-1] >= 4 and self.model_mode == "trained_multiclass":
            predicted_idx = torch.argmax(probabilities, dim=-1).item()
            confidence = probabilities[0][predicted_idx].item()
            raw_label = str(
                self.model.config.id2label.get(predicted_idx, "FACTUAL")
            ).lower()
            label_map = {
                "factual": ClaimType.FACTUAL,
                "opinion": ClaimType.OPINION,
                "mixed": ClaimType.MIXED,
                "numerical": ClaimType.NUMERICAL,
            }
            claim_type = label_map.get(raw_label, ClaimType.FACTUAL)
            return {
                "type": claim_type,
                "confidence": float(confidence),
                "reasoning": "Fine-tuned claim type model prediction",
                "decision_source": "trained_model",
                "scores": {
                    str(self.model.config.id2label.get(idx, idx)).lower(): float(
                        probabilities[0][idx].item()
                    )
                    for idx in range(probabilities.shape[-1])
                },
                "model_confidence": float(confidence),
            }

        if probabilities.shape[-1] < 2:
            return self._heuristic_classify(
                claim,
                decision_source="heuristic_invalid_model_output",
            )

        factual_prob = probabilities[0][0].item()
        opinion_prob = probabilities[0][1].item()
        model_confidence = max(factual_prob, opinion_prob)

        if model_confidence < self.MODEL_CONFIDENCE_THRESHOLD:
            return self._heuristic_classify(
                claim,
                decision_source="heuristic_low_model_confidence",
                model_scores={
                    "factual": float(factual_prob),
                    "opinion": float(opinion_prob),
                    "model_confidence": float(model_confidence),
                },
            )

        if abs(factual_prob - opinion_prob) < self.MIXED_BAND:
            claim_type = ClaimType.MIXED
            confidence = model_confidence
            reasoning = "Mixed factual and opinion elements"
        elif opinion_prob > factual_prob:
            claim_type = ClaimType.OPINION
            confidence = opinion_prob
            reasoning = "Opinion-leaning language"
        else:
            claim_type = ClaimType.FACTUAL
            confidence = factual_prob
            reasoning = "Factual-leaning language"

        if self._has_numerical_content(claim) and claim_type == ClaimType.FACTUAL:
            claim_type = ClaimType.NUMERICAL
            reasoning = "Numerical/statistical factual claim"

        return {
            "type": claim_type,
            "confidence": float(confidence),
            "reasoning": reasoning,
            "decision_source": "model",
            "scores": {"factual": float(factual_prob), "opinion": float(opinion_prob)},
            "model_confidence": float(model_confidence),
        }

    def _heuristic_classify(self, claim: str, decision_source="heuristic", model_scores=None) -> dict:
        text = (claim or "").lower()

        opinion_markers = [
            "i think",
            "i believe",
            "best",
            "worst",
            "should",
            "great",
            "terrible",
            "in my opinion",
        ]
        factual_markers = [
            "according to",
            "reported",
            "data",
            "study",
            "percent",
            "population",
            "in ",
        ]

        opinion_hits = sum(1 for w in opinion_markers if w in text)
        factual_hits = sum(1 for w in factual_markers if w in text)

        if self._has_numerical_content(text):
            result = {
                "type": ClaimType.NUMERICAL,
                "confidence": 0.75,
                "reasoning": "Contains numerical/statistical markers",
                "scores": {"factual": 0.75, "opinion": 0.25},
                "decision_source": decision_source,
            }
            if model_scores:
                result["model_scores"] = model_scores
            return result

        if opinion_hits > factual_hits:
            result = {
                "type": ClaimType.OPINION,
                "confidence": 0.7,
                "reasoning": "Opinion markers detected",
                "scores": {"factual": 0.3, "opinion": 0.7},
                "decision_source": decision_source,
            }
            if model_scores:
                result["model_scores"] = model_scores
            return result

        if factual_hits > opinion_hits:
            result = {
                "type": ClaimType.FACTUAL,
                "confidence": 0.7,
                "reasoning": "Factual markers detected",
                "scores": {"factual": 0.7, "opinion": 0.3},
                "decision_source": decision_source,
            }
            if model_scores:
                result["model_scores"] = model_scores
            return result

        result = {
            "type": ClaimType.MIXED,
            "confidence": 0.6,
            "reasoning": "Insufficient signals; treating as mixed",
            "scores": {"factual": 0.5, "opinion": 0.5},
            "decision_source": decision_source,
        }
        if model_scores:
            result["model_scores"] = model_scores
        return result

    @staticmethod
    def _has_numerical_content(text: str) -> bool:
        patterns = [
            r"\d+\s*%",
            r"\d+\s*(million|billion|trillion)",
            r"\d+\s*(deaths?|cases?|people)",
            r"\d+,\d+",
        ]
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)
