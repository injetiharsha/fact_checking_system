def score_document(claim_results):

    true_count = 0
    false_count = 0
    neutral_count = 0

    for result in claim_results:
        if result["final_verdict"] == "TRUE":
            true_count += 1
        elif result["final_verdict"] == "FALSE":
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

    score = (true_count - false_count) / total

    if score > 0.6:
        verdict = "Highly Reliable"
    elif score > 0.2:
        verdict = "Mostly Reliable"
    elif score >= -0.2:
        verdict = "Mixed"
    elif score >= -0.6:
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
