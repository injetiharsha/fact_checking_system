import re


def extract_year(text):
    years = re.findall(r'(?:19|20)\d{2}', text or "")
    return [int(year) for year in years]


def year_reasoning(claim, evidence_text):
    claim_years = extract_year(claim)
    evidence_years = extract_year(evidence_text)

    if len(claim_years) == 1 and len(evidence_years) == 1:
        if claim_years[0] == evidence_years[0]:
            return "SUPPORT"

    return None
