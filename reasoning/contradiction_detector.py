# reasoning/contradiction_detector.py

from verdict.weighted_score import WeightedScorer


class ConflictAnalyzer:

    def __init__(self):
        self.scorer = WeightedScorer()

    def analyze(self, evidence_list):

        if not evidence_list:
            return "Insufficient Evidence"

        support_score, refute_score = self.scorer.compute_score(evidence_list)

        if support_score > refute_score * 1.2:
            return "Strong Supporting Consensus"

        if refute_score > support_score * 1.2:
            return "Strong Contradictory Evidence"

        if support_score > 0 and refute_score > 0:
            return "Conflicting Evidence Present"

        return "Insufficient Evidence"