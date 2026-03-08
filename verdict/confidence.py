# verdict/confidence.py

class ConfidenceCalculator:

    def __init__(self):
        pass

    def calculate(self, support_score, refute_score, score_gap_threshold=0.15):

        total = support_score + refute_score

        if total == 0:
            return 0

        raw = abs(support_score - refute_score) / total

        # Penalize close-score situations to avoid overconfident outputs.
        gap = abs(support_score - refute_score)
        if gap < score_gap_threshold:
            raw *= 0.75

        return round(raw, 3)
