# semantic/stance_model.py

import re
import sys
from models.stance.nli_model import NLIModel


class StanceDetector:
    MODEL_STANCE_MIN_CONFIDENCE = 0.55
    LEXICAL_RESCUE_MIN_OVERLAP = 2
    SUPPORT_MIN_CONFIDENCE = 0.72
    REFUTE_MIN_CONFIDENCE = 0.58
    CAPITAL_ALIASES = {
        "bangalore": "bengaluru",
        "bengaluru": "bengaluru",
        "bombay": "mumbai",
        "mumbai": "mumbai",
        "madras": "chennai",
        "chennai": "chennai",
        "delhi": "new delhi",
        "new delhi": "new delhi",
        "hyderabad": "hyderabad",
        "kolkata": "kolkata",
        "calcutta": "kolkata",
    }
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

        neutral_rescue = self._neutral_refute_rescue(claim, evidence, overlap)
        if neutral_rescue is not None:
            return {"stance": neutral_rescue, "confidence": 0.62, "source": "heuristic_refute_rescue"}

        if overlap >= self.LEXICAL_RESCUE_MIN_OVERLAP and any(c in text for c in refute_cues):
            return {"stance": "REFUTE", "confidence": 0.62, "source": "heuristic_refute_rescue"}

        return {
            "stance": "NEUTRAL",
            "confidence": round(confidence, 3),
            "source": f"model_low_confidence_or_neutral:{self.model.model_name or 'unknown'}",
        }

    def detect_many(self, evidences, claim):
        clipped = [(evidence or "")[:800] for evidence in evidences]
        predictions = self.model.predict_many(claim, clipped)
        results = []
        for evidence, (label, confidence) in zip(clipped, predictions):
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
            stance = stance_map.get(label, "NEUTRAL")
            filtered = self._postfilter_model_stance(
                stance=stance,
                confidence=float(confidence),
                claim=claim,
                evidence=evidence,
            )
            if filtered is not None:
                results.append({
                    "stance": filtered,
                    "confidence": round(confidence, 3),
                    "source": f"model:{self.model.model_name or 'unknown'}",
                })
                continue

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
            neutral_rescue = self._neutral_refute_rescue(claim, evidence, overlap)
            if neutral_rescue is not None:
                results.append({"stance": neutral_rescue, "confidence": 0.62, "source": "heuristic_refute_rescue"})
                continue
            if overlap >= self.LEXICAL_RESCUE_MIN_OVERLAP and any(c in text for c in refute_cues):
                results.append({"stance": "REFUTE", "confidence": 0.62, "source": "heuristic_refute_rescue"})
                continue

            results.append({
                "stance": "NEUTRAL",
                "confidence": round(confidence, 3),
                "source": f"model_low_confidence_or_neutral:{self.model.model_name or 'unknown'}",
            })
        return results

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

    def _canonical_place(self, text):
        normalized_text = (text or "").lower()
        normalized_text = re.sub(r"\([^)]*\)", " ", normalized_text)
        normalized_text = re.sub(r",\s*(?:also\s+known\s+as|formerly\s+known\s+as|officially\s+known\s+as)[^,]*,?", " ", normalized_text)
        if "," in normalized_text:
            normalized_text = normalized_text.split(",", 1)[0]
        normalized = " ".join(re.findall(r"[a-z]+", normalized_text))
        normalized = re.sub(r"^(the\s+)?(indian\s+state\s+of|state\s+of|union\s+territory\s+of|national\s+capital\s+territory\s+of)\s+", "", normalized)
        if normalized in self.CAPITAL_ALIASES:
            return self.CAPITAL_ALIASES[normalized]
        for alias, canonical in sorted(self.CAPITAL_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
            if normalized.endswith(f" {alias}") or normalized.startswith(f"{alias} "):
                return canonical
        return normalized

    def _extract_capital_relation(self, text):
        normalized = " ".join((text or "").lower().replace("-", " ").split())
        normalized = re.sub(r"\([^)]*\)", " ", normalized)
        normalized = re.sub(
            r",\s*(?:also\s+known\s+as|formerly\s+known\s+as|officially\s+known\s+as)[^,]*,?",
            " ",
            normalized,
        )
        normalized = re.sub(r",\s*", " ", normalized)
        patterns = (
            r"(?P<subject>[a-z\s]+?)\s+is\s+(?:the\s+)?(?P<qualifier>(?:financial|technology|tech|cultural|summer|second|state|joint|common)\s+)?capital(?:\s+city)?\s+of\s+(?P<target>(?:the\s+)?(?:indian\s+state\s+of|state\s+of|union\s+territory\s+of|national\s+capital\s+territory\s+of)?\s*[a-z\s]+)",
            r"(?:the\s+)?(?P<qualifier>(?:financial|technology|tech|cultural|summer|second|state|joint|common)\s+)?capital(?:\s+city)?\s+of\s+(?P<target>(?:the\s+)?(?:indian\s+state\s+of|state\s+of|union\s+territory\s+of|national\s+capital\s+territory\s+of)?\s*[a-z\s]+?)\s+is\s+(?P<subject>[a-z\s]+)",
        )
        for pattern in patterns:
            match = re.search(pattern, normalized)
            if not match:
                continue
            subject = self._canonical_place(match.group("subject"))
            target = self._canonical_place(match.group("target"))
            qualifier = " ".join((match.groupdict().get("qualifier") or "").split()).strip()
            relation = f"{qualifier}_capital".strip("_") if qualifier else "official_capital"
            if subject and target:
                return {"subject": subject, "target": target, "relation": relation}
        return None

    def _has_qualified_capital_language(self, text):
        normalized = " ".join((text or "").lower().split())
        if "silicon valley" in normalized:
            return True
        patterns = (
            r"\bfinancial(?:,\s*[a-z]+)*(?:\s+and\s+[a-z]+)*\s+capital\b",
            r"\btechnology(?:,\s*[a-z]+)*(?:\s+and\s+[a-z]+)*\s+capital\b",
            r"\btech(?:,\s*[a-z]+)*(?:\s+and\s+[a-z]+)*\s+capital\b",
            r"\bcultural(?:,\s*[a-z]+)*(?:\s+and\s+[a-z]+)*\s+capital\b",
            r"\bsummer\s+capital\b",
            r"\bsecond\s+capital\b",
            r"\bstate\s+capital\b",
            r"\bjoint\s+capital\b",
            r"\bcommon\s+capital\b",
        )
        return any(re.search(pattern, normalized) for pattern in patterns)

    def _extract_is_a_predicate(self, text):
        normalized = " ".join((text or "").lower().replace("-", " ").split())
        match = re.search(r"\b[a-z\s]+?\s+is\s+(?:a|an|the)\s+([a-z\s]+?)(?:\.|,|;|$)", normalized)
        if not match:
            return None
        predicate = " ".join(re.findall(r"[a-z]+", match.group(1))).strip()
        predicate = re.sub(r"\b(?:that|which|who|because|and|but)\b.*$", "", predicate).strip()
        return predicate or None

    def _extract_than_comparison(self, text):
        normalized = " ".join((text or "").lower().replace("-", " ").split())
        patterns = (
            r"(?P<subject>[a-z\s]+?)\s+is\s+(?P<cmp>longer|shorter|larger|smaller|older|younger|deeper|higher|taller)\s+than\s+(?P<object>[a-z\s]+?)(?:\.|,|;|$)",
            r"(?P<subject>[a-z\s]+?)\s+are\s+(?P<cmp>longer|shorter|larger|smaller|older|younger|deeper|higher|taller)\s+than\s+(?P<object>[a-z\s]+?)(?:\.|,|;|$)",
        )
        for pattern in patterns:
            match = re.search(pattern, normalized)
            if not match:
                continue
            subject = " ".join(re.findall(r"[a-z]+", match.group("subject"))).strip()
            obj = " ".join(re.findall(r"[a-z]+", match.group("object"))).strip()
            cmp_word = match.group("cmp").strip()
            if subject and obj and cmp_word:
                return {"subject": subject, "object": obj, "cmp": cmp_word}
        return None

    def _has_reporting_quote_context(self, text):
        normalized = (text or "").lower()
        reporting_markers = (
            " said ", " says ", " declared ", " wrote ", " tweeted ", " posted ",
            " claimed ", " joke", " joked ", " laughed", " according to ", " i saw ",
            " quote", " quoted ", " asked ", " told ", " described ", " calling ",
        )
        quote_markers = ('“', '”', '"', "'")
        has_quote = any(marker in (text or "") for marker in quote_markers)
        return has_quote and any(marker in normalized for marker in reporting_markers)

    def _neutral_refute_rescue(self, claim, evidence, overlap):
        if overlap < self.LEXICAL_RESCUE_MIN_OVERLAP:
            return None

        claim_text = (claim or "").lower()
        evidence_text = (evidence or "").lower()

        claim_capital = self._extract_capital_relation(claim_text)
        evidence_capital = self._extract_capital_relation(evidence_text)
        if claim_capital and evidence_capital:
            same_subject = claim_capital["subject"] == evidence_capital["subject"]
            same_target = claim_capital["target"] == evidence_capital["target"]
            if same_subject and not same_target:
                return "REFUTE"
            if same_target and not same_subject and evidence_capital.get("relation") == "official_capital":
                return "REFUTE"

        predicate = self._extract_is_a_predicate(claim_text)
        if predicate:
            direct_negations = (
                f"not a {predicate}",
                f"not an {predicate}",
                f"not the {predicate}",
                f"neither a {predicate}",
                f"nor a {predicate}",
                f"rather than a {predicate}",
                f"rather than being a {predicate}",
            )
            if any(marker in evidence_text for marker in direct_negations):
                return "REFUTE"

        comparison = self._extract_than_comparison(claim_text)
        if comparison and comparison["cmp"] == "longer":
            subject = comparison["subject"]
            obj = comparison["object"]
            if subject in evidence_text and obj in evidence_text:
                if "second longest" in evidence_text or "second-longest" in evidence_text:
                    if f"longest river is the {obj}" in evidence_text or f"with the {subject}" in evidence_text:
                        return "REFUTE"

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
        claim_capital = self._extract_capital_relation(claim_text)
        evidence_capital = self._extract_capital_relation(text)

        if claim_capital and evidence_capital:
            same_subject = claim_capital["subject"] == evidence_capital["subject"]
            same_target = claim_capital["target"] == evidence_capital["target"]
            claim_relation = claim_capital.get("relation")
            evidence_relation = evidence_capital.get("relation")
            if claim_relation == "official_capital":
                if same_subject and not same_target:
                    return "REFUTE"
                if same_target and not same_subject and evidence_relation == "official_capital":
                    return "REFUTE"
                if evidence_relation != "official_capital":
                    if same_subject or same_target:
                        return None
            elif evidence_relation == "official_capital":
                if same_subject and not same_target:
                    return "REFUTE"

        if claim_cmp and claim_rank and evidence_rank and evidence_rank != claim_rank:
            return "REFUTE"

        if stance == "SUPPORT":
            if self._has_reporting_quote_context(text):
                return None
            if claim_capital and self._has_qualified_capital_language(text):
                return None
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


