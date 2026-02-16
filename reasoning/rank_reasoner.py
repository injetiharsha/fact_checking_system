import re
import inflect

p = inflect.engine()


def extract_all_ranks(text):
    text = text.lower().replace("-", " ")

    ranks = []

    # Numeric ordinals (5th, 21st, etc.)
    for match in re.findall(r'(\d+)(st|nd|rd|th)', text):
        ranks.append(int(match[0]))

    # Word ordinals (first, second, fourth, etc.)
    words = text.split()
    for word in words:
        try:
            number = p.ordinal_to_number(word)
            if number:
                ranks.append(int(number))
        except:
            continue

    return ranks


def numeric_rank_reasoning(claim, evidence_text):
    claim_ranks = extract_all_ranks(claim)
    evidence_ranks = extract_all_ranks(evidence_text)

    if not claim_ranks or not evidence_ranks:
        return None

    claim_rank = claim_ranks[0]

    if claim_rank in evidence_ranks:
        return "SUPPORT"
    else:
        return "REFUTE"
