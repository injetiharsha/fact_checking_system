# claim_detection/normalizer.py

import re


def normalize_claim(claim: str) -> str:
    """
    Normalize claim text for better reasoning consistency.
    """

    if not claim:
        return ""

    # Lowercase
    claim = claim.lower()

    # Remove extra spaces
    claim = re.sub(r"\s+", " ", claim)

    # Remove unnecessary symbols (keep % and $)
    claim = re.sub(r"[^\w\s\$\%\.\-]", "", claim)

    return claim.strip()
