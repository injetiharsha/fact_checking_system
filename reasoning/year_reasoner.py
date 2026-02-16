import re

def extract_year(text):
    match = re.search(r'(19|20)\d{2}', text)
    if match:
        return int(match.group())
    return None


def year_reasoning(claim, evidence_text):
    claim_year = extract_year(claim)
    evidence_year = extract_year(evidence_text)

    if claim_year and evidence_year:
        if claim_year != evidence_year:
            return "NEUTRAL"

    return None
