import re
import inflect

p = inflect.engine()

COMPARATIVE_MARKERS = {
    "largest", "biggest", "tallest", "deepest", "oldest", "longest",
    "smallest", "youngest", "highest", "lowest",
}
STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "in", "on", "of",
    "to", "and", "than", "after", "before", "with", "from",
}


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

    return ranks


def _content_tokens(text):
    return {
        token for token in re.findall(r"[a-z0-9]+", (text or "").lower())
        if len(token) > 2 and token not in STOPWORDS and not token.isdigit()
    }


def _comparative_markers(text):
    tokens = set(re.findall(r"[a-z]+", (text or "").lower().replace("-", " ")))
    return tokens & COMPARATIVE_MARKERS


def numeric_rank_reasoning(claim, evidence_text):

    claim_ranks = extract_all_ranks(claim)
    evidence_ranks = extract_all_ranks(evidence_text)
    claim_tokens = _content_tokens(claim)
    evidence_tokens = _content_tokens(evidence_text)
    claim_markers = _comparative_markers(claim)
    evidence_markers = _comparative_markers(evidence_text)

    overlap = claim_tokens & evidence_tokens
    if (
        not claim_ranks
        or not evidence_ranks
        or len(overlap) < 2
        or (claim_markers and evidence_markers and not (claim_markers & evidence_markers))
    ):
        return None

    claim_rank = claim_ranks[0]
    evidence_rank = evidence_ranks[0]

    # Keep this rescue narrow: only trust explicit ordinal/number evidence.
    # Qualitative rank words such as "largest" often appear in related but
    # non-answer sentences (for example, "largest moon" beside the real subject).
    if claim_rank == 1 and not re.search(r"\b(first|1st|number one|#1)\b", (evidence_text or "").lower()):
        return None

    if evidence_rank == claim_rank:
        return "SUPPORT"
    if claim_rank != evidence_rank and claim_markers:
        return "REFUTE"
    return None
