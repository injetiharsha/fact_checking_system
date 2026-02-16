# verdict/aggregate.py

def aggregate_results(evidence_results):
    support_score = 0
    refute_score = 0

    for item in evidence_results:
        weighted = item["weight"] * item["confidence"]

        if item["stance"] == "SUPPORT":
            support_score += weighted
        elif item["stance"] == "REFUTE":
            refute_score += weighted

    total = support_score + refute_score

    if total == 0:
        return "NEUTRAL", 0.0

    if support_score > refute_score:
        verdict = "TRUE"
        confidence = support_score / total
    else:
        verdict = "FALSE"
        confidence = refute_score / total

    return verdict, round(confidence, 3)

