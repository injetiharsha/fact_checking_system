import re

class ClaimExtractor:
    def extract_claims(self, document_text):
        # Remove citation markers like [49]
        clean_text = re.sub(r'\[\d+\]', '', document_text)

        # Split on sentence boundaries and semicolons
        parts = re.split(r'(?<=[.!?])\s+|;\s+', clean_text)

        claims = []

        for part in parts:
            part = part.strip()

            # Skip empty fragments
            if not part:
                continue

            claims.append(part)

        return claims[:15]  # increase slightly
