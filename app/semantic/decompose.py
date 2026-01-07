import re

def decompose_claim(claim: str):
    """
    Splits a complex claim into atomic factual statements
    using linguistic separators only.
    No semantics, no rules, no assumptions.
    """

    if not claim or len(claim.strip()) < 10:
        return [claim]

    separators = [
        r"\band\b",
        r"\bbut\b",
        r"\bwhile\b",
        r"\balthough\b",
        r"\bhowever\b",
        r"\bwhich\b",
        r","
    ]

    pattern = "|".join(separators)

    parts = re.split(pattern, claim, flags=re.IGNORECASE)

    subclaims = [
        p.strip()
        for p in parts
        if len(p.strip()) > 8
    ]

    return subclaims if subclaims else [claim]
