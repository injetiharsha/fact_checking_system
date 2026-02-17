class WeightedScorer:

    def __init__(self, min_evidence=1):
        self.min_evidence = min_evidence

    def compute_score(self, evidence_list):

        support_score = 0
        refute_score = 0

        strong_evidence_count = 0

        for ev in evidence_list:

            stance = ev.get("stance")
            weight = ev.get("weight", 0)
            confidence = ev.get("confidence", 0)

            final_strength = weight * confidence

            # Ignore very weak evidence
            if final_strength < 0.2:
                continue

            strong_evidence_count += 1

            if stance == "SUPPORT":
                support_score += final_strength

            elif stance == "REFUTE":
                refute_score += final_strength

        # If not enough evidence → Neutral
        if strong_evidence_count < self.min_evidence:
            return 0, 0

        return round(support_score, 3), round(refute_score, 3)
