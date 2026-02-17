# verdict/final_report.py

from verdict.weighted_score import WeightedScorer
from verdict.confidence import ConfidenceCalculator


class FinalVerdictEngine:

    def __init__(self):
        self.scorer = WeightedScorer()
        self.confidence_calc = ConfidenceCalculator()

    def decide(self, evidence_list):

        support_score, refute_score = self.scorer.compute_score(evidence_list)

        if support_score > refute_score:
            verdict = "TRUE"
        elif refute_score > support_score:
            verdict = "FALSE"
        else:
            verdict = "NEUTRAL"

        confidence = self.confidence_calc.calculate(
            support_score,
            refute_score
        )

        return verdict, confidence
