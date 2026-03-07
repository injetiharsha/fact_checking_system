# evidence/quality.py

class QualityScorer:

    def __init__(self):
        pass

    def score(self, text):

        if not text:
            return 0

        words = text.split()
        length = len(words)

        score = 0

        if length > 30:
            score += 0.4

        if length > 80:
            score += 0.1

        if any(char.isdigit() for char in text):
            score += 0.2

        if "." in text:
            score += 0.3

        return min(score, 1.0)