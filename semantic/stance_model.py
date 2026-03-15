# semantic/stance_model.py

import re
import sys
from models.stance.nli_model import NLIModel


class StanceDetector:
    MODEL_STANCE_MIN_CONFIDENCE = 0.55
    LEXICAL_RESCUE_MIN_OVERLAP = 2
    SUPPORT_MIN_CONFIDENCE = 0.72
    REFUTE_MIN_CONFIDENCE = 0.58

    def __init__(self, v2_mode=False):
        self.model = NLIModel()
        self.v2_mode = v2_mode

    def detect(self, evidence, claim):
        evidence = (evidence or "")[:800]

        # Model expects (claim, evidence)
        label, confidence = self.model.predict(claim, evidence)
        label = (label or "NEUTRAL").upper()

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

        print("\nNLI INPUT")
        safe_claim = (claim or "").replace("\ufeff", "").encode(
            sys.stdout.encoding or "utf-8",
            errors="replace",
        ).decode(sys.stdout.encoding or "utf-8", errors="replace")
        safe_evidence = (evidence or "").replace("\ufeff", "").encode(
            sys.stdout.encoding or "utf-8",
            errors="replace",
        ).decode(sys.stdout.encoding or "utf-8", errors="replace")
        print("Claim:", safe_claim)
        print("Evidence:", safe_evidence)
        print("Prediction:", label, confidence)

        stance = stance_map.get(label, "NEUTRAL")
        filtered = self._postfilter_model_stance(
            stance=stance,
            confidence=float(confidence),
            claim=claim,
            evidence=evidence,
        )
        if filtered is not None:
            return {
                "stance": filtered,
                "confidence": round(confidence, 3),
                "source": f"model:{self.model.model_name or 'unknown'}",
            }

        # Conservative lexical fallback only for clear refutations.
        text = (evidence or "").lower()
        claim_text = (claim or "").lower()
        claim_tokens = [
            t for t in re.findall(r"[a-z0-9]+", claim_text)
            if len(t) > 2 and t not in {"the", "and", "for", "with", "from", "that"}
        ]
        overlap = sum(1 for t in claim_tokens if t in text)

        refute_cues = (
            "hoax", "fake", "myth", "false", "debunk", "does not", "doesn't",
            "cannot", "can't", "no evidence", "not true", "incorrect"
        )

        if overlap >= self.LEXICAL_RESCUE_MIN_OVERLAP and any(c in text for c in refute_cues):
            return {"stance": "REFUTE", "confidence": 0.62, "source": "heuristic_refute_rescue"}

        return {
            "stance": "NEUTRAL",
            "confidence": round(confidence, 3),
            "source": f"model_low_confidence_or_neutral:{self.model.model_name or 'unknown'}",
        }

    def _extract_rank_claim(self, text):
        text = (text or "").lower().replace("-", " ")
        patterns = [
            ("largest", 1),
            ("biggest", 1),
            ("deepest", 1),
            ("longest", 1),
            ("oldest", 1),
            ("smallest", 1),
            ("youngest", 1),
        ]
        for token, rank in patterns:
            if token in text:
                return token, rank
        return None, None

    def _extract_rank_evidence(self, text):
        text = (text or "").lower().replace("-", " ")
        order_words = {
            "first": 1,
            "second": 2,
            "third": 3,
            "fourth": 4,
            "fifth": 5,
        }
        for word, number in order_words.items():
            if word in text:
                return number
        match = re.search(r"\b(\d+)(st|nd|rd|th)\b", text)
        if match:
            return int(match.group(1))
        return None

    def _postfilter_model_stance(self, stance, confidence, claim, evidence):
        if stance == "NEUTRAL":
            return None

        text = (evidence or "").lower()
        claim_text = (claim or "").lower()
        claim_tokens = {
            t for t in re.findall(r"[a-z0-9]+", claim_text)
            if len(t) > 2 and t not in {"the", "and", "for", "with", "from", "that"}
        }
        evidence_tokens = set(re.findall(r"[a-z0-9]+", text))
        token_overlap = len(claim_tokens & evidence_tokens)

        shape_claim = any(
            token in claim_tokens
            for token in {"flat", "round", "sphere", "spherical", "globe"}
        )
        shape_refute_terms = {"sphere", "spherical", "round", "globe", "hemisphere", "ellipsoid"}
        generic_structure_terms = {
            "crust", "mantle", "core", "equator", "prime", "meridian",
            "hemisphere", "northern", "southern", "western", "eastern",
        }
        claim_cmp, claim_rank = self._extract_rank_claim(claim)
        evidence_rank = self._extract_rank_evidence(evidence)

        if claim_cmp and claim_rank and evidence_rank and evidence_rank != claim_rank:
            return "REFUTE"

        if stance == "SUPPORT":
            if self.v2_mode and self._has_explicit_refute_language(text):
                return None
            if self._has_temporal_support_anchor(claim_text, text, token_overlap, confidence):
                return "SUPPORT"
            if confidence < self.SUPPORT_MIN_CONFIDENCE:
                return None
            if shape_claim and any(term in evidence_tokens for term in shape_refute_terms):
                return None
            if any(term in evidence_tokens for term in generic_structure_terms) and token_overlap < 2:
                return None
            return "SUPPORT"

        if stance == "REFUTE":
            if confidence >= self.REFUTE_MIN_CONFIDENCE:
                return "REFUTE"
            if shape_claim and any(term in evidence_tokens for term in shape_refute_terms):
                return "REFUTE"
            return None

        return None

    def _has_explicit_refute_language(self, text):
        refute_markers = (
            "does not",
            "doesn't",
            "will not",
            "cannot",
            "can't",
            "not protect",
            "not prevent",
            "not cure",
            "no evidence",
            "false",
            "myth",
            "hoax",
            "debunk",
            "dangerous",
        )
        return any(marker in (text or "") for marker in refute_markers)

    def _has_temporal_support_anchor(self, claim_text, evidence_text, token_overlap, confidence):
        if confidence < 0.58 or token_overlap < 2:
            return False
        temporal_claim = (
            bool(re.search(r"\b(?:19|20)\d{2}\b", claim_text))
            or any(token in claim_text for token in ("founded", "established", "fell", "began", "created", "started"))
        )
        temporal_evidence = (
            bool(re.search(r"\b(?:19|20)\d{2}\b", evidence_text))
            or any(token in evidence_text for token in ("founded", "established", "fell", "began", "created", "started", "officially began"))
        )
        return temporal_claim and temporal_evidence


