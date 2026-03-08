import re


class ClaimExtractor:
    def __init__(self, max_claims=6):
        self.max_claims = max_claims

    def extract_claims(self, document_text):
        if not document_text:
            return []

        # Remove citation markers like [49]
        clean_text = re.sub(r'\[\d+\]', '', document_text)
        clean_text = re.sub(r"\s+", " ", clean_text).strip()

        # Split on sentence boundaries, newlines, and semicolons.
        parts = re.split(r'(?<=[.!?])\s+|;\s+|\n+', clean_text)

        claims = []
        seen = set()

        for part in parts:
            part = part.strip()

            if not part:
                continue

            # Drop boilerplate/navigation-like fragments.
            words = part.split()
            if len(words) < 5 or len(words) > 45:
                continue
            if sum(ch.isdigit() for ch in part) > 12:
                continue
            lowered = part.lower()
            noisy_terms = (
                "timeline", "premium", "calendar", "login", "subscribe",
                "privacy policy", "terms of use", "sports", "weather", "tv"
            )
            if any(term in lowered for term in noisy_terms):
                continue

            key = re.sub(r"[^a-z0-9\u0B80-\u0BFF]+", " ", lowered).strip()
            if not key or key in seen:
                continue
            seen.add(key)
            claims.append(part)

            if len(claims) >= self.max_claims:
                break

        return claims

    def extract_main_claim(self, document_text):
        claims = self.extract_claims(document_text)
        if not claims:
            return None

        # Prefer a medium-length declarative sentence with rich tokens.
        def score(sentence):
            words = sentence.split()
            token_diversity = len(set(w.lower() for w in words)) / max(len(words), 1)
            declarative_bonus = 0.15 if sentence.endswith(".") else 0.0
            length_score = 1.0 - abs(len(words) - 18) / 18.0
            return (length_score * 0.6) + (token_diversity * 0.25) + declarative_bonus

        best = max(claims, key=score)
        return best

