# evidence/quality.py
import re


class QualityScorer:

    def __init__(self):
        pass

    def score(self, text):

        if not text:
            return 0

        normalized = " ".join((text or "").split())
        lowered = normalized.lower()
        words = normalized.split()
        length = len(words)

        score = 0

        if length >= 12:
            score += 0.25

        if length > 30:
            score += 0.4

        if length > 80:
            score += 0.1

        if any(char.isdigit() for char in normalized):
            score += 0.2

        if "." in normalized:
            score += 0.15

        if any(token in lowered for token in (" is ", " are ", " was ", " were ", " has ", " have ", " can ", " cannot ", " does not ")):
            score += 0.2

        if re.search(r"\b(?:according to|reportedly|during a speech|watch live|min read)\b", lowered):
            score -= 0.15

        metadata_markers = (
            "document id",
            "publication date",
            "distribution limits",
            "subject category",
            "no preview available",
            "image credit",
            "photo credit",
            "copyright",
            "this article is for students",
        )
        if any(marker in lowered for marker in metadata_markers):
            score -= 0.35

        if normalized.endswith("?"):
            score -= 0.15

        return min(score, 1.0)
