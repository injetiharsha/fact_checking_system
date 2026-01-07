import numpy as np


def cosine_similarity(vec1, vec2):
    return float(np.dot(vec1, vec2))


def filter_by_similarity(claim_embedding, evidence, threshold=0.45):
    """
    Filters evidence by semantic relevance to the claim.
    This is a HARD GATE — irrelevant evidence must not pass.
    """
    relevant = []

    for e in evidence:
        emb = e.get("embedding")
        if emb is None:
            continue

        score = cosine_similarity(claim_embedding, emb)
        if score >= threshold:
            e["similarity"] = round(score, 3)
            relevant.append(e)

    return relevant


def rank_evidence(evidence):
    """
    Rank evidence by combined semantic relevance and stance confidence.
    """
    return sorted(
        evidence,
        key=lambda e: (
            e.get("similarity", 0) * e.get("confidence", 1)
        ),
        reverse=True
    )
