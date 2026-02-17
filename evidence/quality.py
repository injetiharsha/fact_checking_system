# evidence/quality.py

class QualityScorer:

    def __init__(self):
        pass

    def score(self, text):

        if not text:
            return 0

        length = len(text.split())

        # very short = low quality
        if length < 20:
            return 0.2

        # medium length
        if length < 100:
            return 0.6

        return 1.0
