def consensus_verdict(stances):
    if not stances:
        return "UNVERIFIED", 0.0

    support = [s for s in stances if s["label"] == "supports"]
    contradict = [s for s in stances if s["label"] == "contradicts"]

    total = len(stances)

    if len(support) >= 2 and not contradict:
        return "TRUE", len(support) / total

    if len(contradict) >= 2 and not support:
        return "FALSE", len(contradict) / total

    if support and contradict:
        return "PARTIALLY TRUE", max(len(support), len(contradict)) / total

    return "UNVERIFIED", 0.3
