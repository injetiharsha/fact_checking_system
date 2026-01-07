def calibrate_confidence(verdict: str, stances: list):
    """
    Converts raw stance signals into conservative confidence.
    """

    if not stances:
        return 0.1

    support = [s for s in stances if s["label"] == "supports"]
    contradict = [s for s in stances if s["label"] == "contradicts"]

    total = len(stances)

    agreement_ratio = max(len(support), len(contradict)) / total

    avg_stance_conf = sum(s["confidence"] for s in stances) / total

    base = agreement_ratio * avg_stance_conf

    if verdict == "TRUE":
        confidence = base
    elif verdict == "FALSE":
        confidence = base
    elif verdict == "PARTIALLY TRUE":
        confidence = base * 0.7
    else:
        confidence = base * 0.4

    return round(min(confidence, 0.95), 2)
