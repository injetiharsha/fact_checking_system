# verdict/confidence.py

class ConfidenceCalculator:

    def __init__(self):
        pass

    def calculate(self, support_score, refute_score):

        total = support_score + refute_score

        if total == 0:
            return 0

        return round(abs(support_score - refute_score) / total, 3)
