import re
from enum import Enum

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer


class ClaimType(Enum):
    FACTUAL = "factual"
    OPINION = "opinion"
    MIXED = "mixed"
    NUMERICAL = "numerical"


class ClaimTypeClassifier:
    """Claim type classifier with offline-safe fallback."""

    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = None
        self.model = None

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
                print(f"ClaimTypeClassifier using cached model: {model_name}")
                break
            except Exception:
                continue

        if self.model is None:
            print("ClaimTypeClassifier fallback: heuristic mode (no cached model)")

    def classify(self, claim: str) -> dict:
        if self.model is None or self.tokenizer is None:
            return self._heuristic_classify(claim)

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

        if probabilities.shape[-1] < 2:
            return self._heuristic_classify(claim)

        factual_prob = probabilities[0][0].item()
        opinion_prob = probabilities[0][1].item()

        if abs(factual_prob - opinion_prob) < 0.15:
            claim_type = ClaimType.MIXED
            confidence = 0.65
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
            "scores": {"factual": float(factual_prob), "opinion": float(opinion_prob)},
        }

    def _heuristic_classify(self, claim: str) -> dict:
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
            return {
                "type": ClaimType.NUMERICAL,
                "confidence": 0.75,
                "reasoning": "Contains numerical/statistical markers",
                "scores": {"factual": 0.75, "opinion": 0.25},
            }

        if opinion_hits > factual_hits:
            return {
                "type": ClaimType.OPINION,
                "confidence": 0.7,
                "reasoning": "Opinion markers detected",
                "scores": {"factual": 0.3, "opinion": 0.7},
            }
        if factual_hits > opinion_hits:
            return {
                "type": ClaimType.FACTUAL,
                "confidence": 0.7,
                "reasoning": "Factual markers detected",
                "scores": {"factual": 0.7, "opinion": 0.3},
            }

        return {
            "type": ClaimType.MIXED,
            "confidence": 0.6,
            "reasoning": "Insufficient signals; treating as mixed",
            "scores": {"factual": 0.5, "opinion": 0.5},
        }

    @staticmethod
    def _has_numerical_content(text: str) -> bool:
        patterns = [
            r"\d+\s*%",
            r"\d+\s*(million|billion|trillion)",
            r"\d+\s*(deaths?|cases?|people)",
            r"\d+,\d+",
        ]
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)
