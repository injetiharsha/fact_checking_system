# verdict/weighted_score.py

class WeightedScorer:

    def __init__(self, min_evidence=1):
        self.min_evidence = min_evidence

    @staticmethod
    def _final_strength(ev):
        weight = float(ev.get("weight", 0) or 0)
        confidence = float(ev.get("confidence", 0) or 0)
        base_strength = weight * confidence

        quality_signal = float(ev.get("combined_score", 0) or 0)
        if quality_signal <= 0:
            relevance = float(ev.get("relevance_score", 0) or 0)
            quality = float(ev.get("quality_score", 0) or 0)
            quality_signal = relevance * quality

        blended_strength = (base_strength * 0.8) + (quality_signal * 0.2)

        evidence_tier = str(ev.get("evidence_tier") or "").lower()
        if evidence_tier == "strong":
            blended_strength += 0.03

        same_direction_passages = 0
        stance = ev.get("stance")
        if stance == "SUPPORT":
            same_direction_passages = int(ev.get("support_passages", 0) or 0)
        elif stance == "REFUTE":
            same_direction_passages = int(ev.get("refute_passages", 0) or 0)
        if same_direction_passages > 1:
            blended_strength += min(0.08, 0.03 * (same_direction_passages - 1))

        return round(min(1.0, blended_strength), 4)

    def compute_score(self, evidence_list):

        support_score = 0
        refute_score = 0

        strong_evidence_count = 0

        for ev in evidence_list:

            stance = ev.get("stance")

            if stance == "NEUTRAL":
                continue

            final_strength = self._final_strength(ev)

            if final_strength < 0.2:
                continue

            strong_evidence_count += 1

            if stance == "SUPPORT":
                support_score += final_strength
            elif stance == "REFUTE":
                refute_score += final_strength

        if strong_evidence_count < self.min_evidence:
            return 0, 0

        return round(support_score, 3), round(refute_score, 3)
