import re
import inflect

p = inflect.engine()


def extract_all_ranks(text):
    text = text.lower().replace("-", " ")
    ranks = []

    # detect standalone numbers
    for match in re.findall(r'\b\d+\b', text):
        ranks.append(int(match))

    # numeric ordinals (5th, 21st)
    for match in re.findall(r'(\d+)(st|nd|rd|th)', text):
        ranks.append(int(match[0]))

    # word ordinals (first, second)
    for word in text.split():
        try:
            num = p.ordinal_to_number(word)
            if num:
                ranks.append(int(num))
        except:
            continue

    # detect words implying rank 1
    if "largest" in text or "biggest" in text or "tallest" in text:
        ranks.append(1)

    return ranks


def numeric_rank_reasoning(claim, evidence_text):

    claim_ranks = extract_all_ranks(claim)
    evidence_ranks = extract_all_ranks(evidence_text)

    if not claim_ranks or not evidence_ranks:
        return None

    claim_rank = claim_ranks[0]

    evidence_rank = evidence_ranks[0]
    if evidence_rank == claim_rank:
        return "SUPPORT"

    if evidence_rank != claim_rank:
        return "REFUTE"
    return None