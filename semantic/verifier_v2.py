from semantic.stance_model import StanceDetector
from claim_detection.claim_decomposer import ClaimDecomposer


class VerifierV2:
    def __init__(self, stance_detector=None):
        self.stance_detector = stance_detector or StanceDetector(v2_mode=True)
        self.decomposer = ClaimDecomposer()

    def verify(self, claim, sentence_text, context_text=None):
        primary = self.stance_detector.detect(sentence_text, claim)
        if not context_text or context_text.strip() == (sentence_text or "").strip():
            return self._maybe_verify_decomposed_claim(claim, sentence_text, primary)

        contextual = self.stance_detector.detect((context_text or "")[:800], claim)
        primary_stance = primary.get("stance")
        contextual_stance = contextual.get("stance")
        primary_conf = float(primary.get("confidence", 0.0) or 0.0)
        contextual_conf = float(contextual.get("confidence", 0.0) or 0.0)

        if primary_stance == "NEUTRAL" and contextual_stance != "NEUTRAL":
            contextual["source"] = f"verifier_v2_context:{contextual.get('source', 'model')}"
            return contextual

        if (
            primary_stance != "NEUTRAL"
            and contextual_stance != "NEUTRAL"
            and contextual_stance != primary_stance
            and contextual_conf >= primary_conf + 0.12
        ):
            contextual["source"] = f"verifier_v2_context:{contextual.get('source', 'model')}"
            return contextual

        if contextual_stance == primary_stance and contextual_conf > primary_conf:
            contextual["source"] = f"verifier_v2_agree:{contextual.get('source', 'model')}"
            return self._maybe_verify_decomposed_claim(claim, context_text, contextual)

        return self._maybe_verify_decomposed_claim(claim, context_text or sentence_text, primary)

    def _maybe_verify_decomposed_claim(self, claim, evidence_text, base_result):
        if (base_result or {}).get("stance") != "NEUTRAL":
            return base_result

        subclaims = self.decomposer.decompose(claim)
        if len(subclaims) < 2:
            return base_result

        subresults = [self.stance_detector.detect(evidence_text, subclaim) for subclaim in subclaims]
        support_count = sum(1 for row in subresults if row.get("stance") == "SUPPORT")
        refute_count = sum(1 for row in subresults if row.get("stance") == "REFUTE")

        if support_count == len(subresults):
            confidence = sum(float(row.get("confidence", 0.0) or 0.0) for row in subresults) / max(len(subresults), 1)
            return {
                "stance": "SUPPORT",
                "confidence": round(min(0.95, confidence), 3),
                "source": "verifier_v2_decomposed_support",
                "subclaims": subclaims,
            }

        if refute_count > 0 and support_count == 0:
            confidence = sum(
                float(row.get("confidence", 0.0) or 0.0)
                for row in subresults
                if row.get("stance") == "REFUTE"
            ) / max(refute_count, 1)
            return {
                "stance": "REFUTE",
                "confidence": round(min(0.9, confidence), 3),
                "source": "verifier_v2_decomposed_refute",
                "subclaims": subclaims,
            }

        return base_result
