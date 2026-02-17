# reasoning/logical_analyzer.py

import re


class LogicalAnalyzer:

    def __init__(self):
        pass

    def analyze(self, claim: str):
        """
        Analyze logical characteristics of a claim.
        Returns metadata flags.
        """

        claim_lower = claim.lower()

        return {
            "is_future_claim": self._is_future_claim(claim_lower),
            "is_projection": self._is_projection(claim_lower),
            "is_comparative": self._is_comparative(claim_lower),
            "has_numeric_value": self._has_numeric(claim_lower),
            "is_opinion": self._is_opinion(claim_lower)
        }

    # 🔹 Future tense detection
    def _is_future_claim(self, text):
        future_keywords = [
            "will", "going to", "shall",
            "by 2026", "by 2027", "by 2030"
        ]

        return any(keyword in text for keyword in future_keywords)

    # 🔹 Projection / prediction detection
    def _is_projection(self, text):
        projection_keywords = [
            "expected", "predicted",
            "forecast", "estimate",
            "projected"
        ]

        return any(keyword in text for keyword in projection_keywords)

    # 🔹 Comparative detection
    def _is_comparative(self, text):
        comparative_keywords = [
            "largest", "smallest",
            "greater", "less than",
            "more than", "fifth",
            "rank", "top"
        ]

        return any(keyword in text for keyword in comparative_keywords)

    # 🔹 Numeric detection
    def _has_numeric(self, text):
        return bool(re.search(r"\d+", text))

    # 🔹 Opinion detection
    def _is_opinion(self, text):
        opinion_keywords = [
            "best", "worst",
            "amazing", "terrible",
            "great", "bad",
            "believe", "think"
        ]

        return any(keyword in text for keyword in opinion_keywords)
