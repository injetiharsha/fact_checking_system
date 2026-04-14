# semantic/stance_model.py

import os
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
        self.enable_polarized_stance = os.getenv("ENABLE_POLARIZED_STANCE", "0").strip().lower() in {"1", "true", "yes", "on"}
        self.polarized_min_overlap = max(2, int(os.getenv("POLARIZED_STANCE_MIN_OVERLAP", "3")))
        self.polarized_min_confidence = float(os.getenv("POLARIZED_STANCE_MIN_CONFIDENCE", "0.68"))
        self.polarized_support_min_confidence = float(os.getenv("POLARIZED_STANCE_SUPPORT_MIN_CONFIDENCE", "0.72"))

    def _resolved_model_source(self, low_confidence=False):
        model_name = str(getattr(self.model, "model_name", "") or "").strip()
        trained_checkpoint = str(getattr(self.model, "trained_checkpoint", "") or "").strip()
        if model_name and model_name.lower() != "unknown":
            base = model_name
        elif trained_checkpoint:
            base = f"trained_subprocess:{trained_checkpoint}"
        elif getattr(self.model, "trained_checkpoint", None) is not None:
            base = "trained_subprocess:configured_checkpoint"
        else:
            base = "heuristic_fallback"
        prefix = "model_low_confidence_or_neutral" if low_confidence else "model"
        return f"{prefix}:{base}"

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
            "SUPPORTS": "SUPPORT",
            "REFUTE": "REFUTE",
            "REFUTES": "REFUTE",
        }

        # Debug prints removed for speed. Uncomment for debugging.
        # if os.getenv("STANCE_DEBUG", "0") == "1":
        #     print("\nNLI INPUT")
        #     print("Claim:", claim)
        #     print("Evidence:", evidence)
        #     print("Prediction:", label, confidence)

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
                "source": self._resolved_model_source(low_confidence=False),
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

        polarized = self._polarize_neutral_stance(
            claim=claim,
            evidence=evidence,
            confidence=float(confidence),
            overlap=overlap,
        )
        if polarized is not None:
            return polarized

        return {
            "stance": "NEUTRAL",
            "confidence": round(confidence, 3),
            "source": self._resolved_model_source(low_confidence=True),
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
                "SUPPORTS": "SUPPORT",
                "REFUTE": "REFUTE",
                "REFUTES": "REFUTE",
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
                    "source": self._resolved_model_source(low_confidence=False),
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

            polarized = self._polarize_neutral_stance(
                claim=claim,
                evidence=evidence,
                confidence=float(confidence),
                overlap=overlap,
            )
            if polarized is not None:
                results.append(polarized)
                continue

            results.append({
                "stance": "NEUTRAL",
                "confidence": round(confidence, 3),
                "source": self._resolved_model_source(low_confidence=True),
            })
        return results

    def _extract_rank_claim(self, text):
        text = (text or "").lower().replace("-", " ")
        ordinal_words = {
            "first": 1,
            "second": 2,
            "third": 3,
            "fourth": 4,
            "fifth": 5,
        }

        match = re.search(r"\b(\d+)(?:st|nd|rd|th)\s+(?:largest|biggest|deepest|longest|oldest|smallest|youngest)\b", text)
        if match:
            return match.group(1), int(match.group(1))

        for word, number in ordinal_words.items():
            if re.search(rf"\b{word}\s+(?:largest|biggest|deepest|longest|oldest|smallest|youngest)\b", text):
                return word, number

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

        comparator_patterns = [
            r"\b(?P<rank>\d+)(?:st|nd|rd|th)?\s+(?:largest|biggest|deepest|longest|oldest|smallest|youngest)\b",
            r"\b(?P<rank>first|second|third|fourth|fifth)\s+(?:largest|biggest|deepest|longest|oldest|smallest|youngest)\b",
            r"\b(?:largest|biggest|deepest|longest|oldest|smallest|youngest)\s+(?:economy|economies|country|countries|rank|position)?\s*(?:is|was|at|of|to)?\s*(?P<rank>\d+)(?:st|nd|rd|th)?\b",
            r"\b(?:largest|biggest|deepest|longest|oldest|smallest|youngest)\s+(?:economy|economies|country|countries|rank|position)?\s*(?:is|was|at|of|to)?\s*(?P<rank>first|second|third|fourth|fifth)\b",
        ]
        for pattern in comparator_patterns:
            match = re.search(pattern, text)
            if match:
                rank = match.group("rank")
                if rank.isdigit():
                    return int(rank)
                if rank in order_words:
                    return order_words[rank]

        match = re.search(r"\b(\d+)(?:st|nd|rd|th)\b", text)
        if match:
            return int(match.group(1))
        for word, number in order_words.items():
            if re.search(rf"\b{word}\s+rank\b", text):
                return number
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
                # Keep quoted/reporting snippets conservative, but allow high-overlap direct assertions.
                if token_overlap < 4 or confidence < 0.58:
                    return None
            if claim_capital and self._has_qualified_capital_language(text):
                return None
            if self.v2_mode and self._has_explicit_refute_language(text):
                return None
            if self._has_temporal_support_anchor(claim_text, text, token_overlap, confidence):
                return "SUPPORT"
            support_threshold = self.SUPPORT_MIN_CONFIDENCE
            model_name = str(getattr(self.model, "model_name", "") or "").strip().lower()
            fallback_model = model_name in {"", "unknown"}
            if model_name in {"", "unknown"}:
                # When running with fallback NLI, keep SUPPORT conservative but not overly strict.
                support_threshold = 0.58 if token_overlap >= 3 else 0.62
            if self.v2_mode and not fallback_model:
                support_threshold = max(support_threshold, 0.60)
            if confidence < support_threshold:
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

    def _polarize_neutral_stance(self, claim, evidence, confidence, overlap):
        if not self.enable_polarized_stance:
            return None
        if overlap < self.polarized_min_overlap:
            return None

        claim_text = (claim or "").lower()
        evidence_text = (evidence or "").lower()

        if self._has_reporting_quote_context(evidence_text):
            return None

        if self._has_explicit_refute_language(evidence_text):
            return {
                "stance": "REFUTE",
                "confidence": round(max(0.6, min(float(confidence), 0.74)), 3),
                "source": "polarized_refute_inference",
            }

        support_shapes = (
            " is ",
            " are ",
            " was ",
            " were ",
            " has ",
            " have ",
            " consists of ",
            " refers to ",
        )
        has_support_shape = any(marker in f" {evidence_text} " for marker in support_shapes)
        claim_tokens = {
            t for t in re.findall(r"[a-z0-9]+", claim_text)
            if len(t) > 2 and t not in {"the", "and", "for", "with", "from", "that"}
        }
        evidence_tokens = set(re.findall(r"[a-z0-9]+", evidence_text))
        token_overlap = len(claim_tokens & evidence_tokens)

        if (
            float(confidence) >= self.polarized_support_min_confidence
            and token_overlap >= self.polarized_min_overlap
            and has_support_shape
            and not self._has_explicit_refute_language(evidence_text)
        ):
            return {
                "stance": "SUPPORT",
                "confidence": round(max(0.6, min(float(confidence), 0.76)), 3),
                "source": "polarized_support_inference",
            }

        if (
            float(confidence) >= self.polarized_min_confidence
            and token_overlap >= max(self.polarized_min_overlap + 1, 4)
            and not self._has_explicit_refute_language(evidence_text)
        ):
            return {
                "stance": "SUPPORT",
                "confidence": round(max(0.58, min(float(confidence), 0.7)), 3),
                "source": "polarized_support_inference",
            }

        return None


