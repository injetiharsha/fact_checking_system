from semantic.stance_model import StanceDetector


class VerifierV2:
    def __init__(self, stance_detector=None):
        self.stance_detector = stance_detector or StanceDetector(v2_mode=True)

    def verify(self, claim, sentence_text, context_text=None):
        primary = self.stance_detector.detect(sentence_text, claim)
        if not context_text or context_text.strip() == (sentence_text or "").strip():
            return primary

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
            return contextual

        return primary
