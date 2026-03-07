# verdict/document_scorer.py
def score_document(claim_results):

    true_count = 0
    false_count = 0
    neutral_count = 0

    for result in claim_results:

        verdict = result.get("final_verdict", "NEUTRAL")

        if verdict == "TRUE":
            true_count += 1

        elif verdict == "FALSE":
            false_count += 1

        else:
            neutral_count += 1

    total = len(claim_results)

    if total == 0:
        return {
            "score": 0,
            "verdict": "Insufficient Data",
            "true": 0,
            "false": 0,
            "neutral": 0
        }

    # Neutral reduces confidence
    effective_total = total + (neutral_count * 0.5)

    score = (true_count - false_count) / effective_total

    # Adjusted thresholds for small batches
    if score >= 0.6:
        verdict = "Highly Reliable"

    elif score >= 0.25:
        verdict = "Mostly Reliable"

    elif score > -0.25:
        verdict = "Mixed"

    elif score > -0.6:
        verdict = "Mostly Misleading"

    else:
        verdict = "Highly Misleading"

    return {
        "score": round(score, 3),
        "verdict": verdict,
        "true": true_count,
        "false": false_count,
        "neutral": neutral_count
    }