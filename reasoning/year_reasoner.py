import re


def extract_year(text):
    years = re.findall(r'(?:19|20)\d{2}', text or "")
    return [int(year) for year in years]


def _content_tokens(text):
    stop = {
        "the", "a", "an", "is", "are", "was", "were", "in", "on", "of",
        "to", "and", "after", "before", "from", "with",
    }
    return {
        token for token in re.findall(r"[a-z0-9]+", (text or "").lower())
        if len(token) > 2 and token not in stop and not token.isdigit()
    }


def year_reasoning(claim, evidence_text):
    claim_years = extract_year(claim)
    evidence_years = extract_year(evidence_text)
    claim_tokens = _content_tokens(claim)
    evidence_tokens = _content_tokens(evidence_text)

    if (
        len(claim_years) == 1
        and len(evidence_years) == 1
        and len(claim_tokens & evidence_tokens) >= 1
    ):
        if claim_years[0] == evidence_years[0]:
            return "SUPPORT"

    return None
