# reasoning/contradiction_detector.py

def analyze_conflict(evidence_list):
    support_score = 0
    refute_score = 0

    for ev in evidence_list:
        weighted = ev["weight"] * ev["confidence"]

        if ev["stance"] == "SUPPORT":
            support_score += weighted
        elif ev["stance"] == "REFUTE":
            refute_score += weighted

    if support_score > refute_score * 1.2:
        return "Strong Supporting Consensus"

    if refute_score > support_score * 1.2:
        return "Strong Contradictory Evidence"

    if support_score > 0 and refute_score > 0:
        return "Conflicting Evidence Present"

    return "Insufficient Evidence"
