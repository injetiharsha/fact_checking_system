# verdict/final_report.py

from verdict.weighted_score import WeightedScorer
from verdict.confidence import ConfidenceCalculator


class FinalVerdictEngine:

    def __init__(self):

        self.scorer = WeightedScorer()
        self.confidence_calc = ConfidenceCalculator()
        self.min_total_score_for_definitive_verdict = 0.35
        self.min_score_gap_for_definitive_verdict = 0.15

    def decide(self, evidence_list):

        support_score, refute_score = self.scorer.compute_score(evidence_list)
        total = support_score + refute_score
        gap = abs(support_score - refute_score)

        # Determine verdict
        if support_score == 0 and refute_score == 0:
            verdict = "NEUTRAL"
        elif total < self.min_total_score_for_definitive_verdict:
            verdict = "NEUTRAL"
        elif gap < self.min_score_gap_for_definitive_verdict:
            verdict = "NEUTRAL"

        elif support_score > refute_score:
            verdict = "TRUE"

        elif refute_score > support_score:
            verdict = "FALSE"

        else:
            verdict = "NEUTRAL"

        confidence = self.confidence_calc.calculate(
            support_score,
            refute_score,
            score_gap_threshold=self.min_score_gap_for_definitive_verdict,
        )

        if verdict == "NEUTRAL":
            confidence = min(confidence, 0.55)

        print("\n--- VERDICT AGGREGATION ---")
        print("Support score:", support_score)
        print("Refute score:", refute_score)
        print("Score gap:", round(gap, 3))
        print("Final verdict:", verdict)
        print("Confidence:", confidence)

        return verdict, confidence
