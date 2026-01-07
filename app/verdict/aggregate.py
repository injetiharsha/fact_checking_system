def aggregate_results(results: list):
    verdicts = [r["verdict"] for r in results]
    confidences = [r["confidence"] for r in results]

    if "FALSE" in verdicts:
        final_verdict = "FALSE"
    elif all(v == "TRUE" for v in verdicts):
        final_verdict = "TRUE"
    elif "PARTIALLY TRUE" in verdicts:
        final_verdict = "PARTIALLY TRUE"
    else:
        final_verdict = "UNVERIFIED"

    base_confidence = sum(confidences) / len(confidences)

    disagreement_penalty = 0.15 * (
        len(set(verdicts)) - 1
    )

    final_confidence = max(
        round(base_confidence - disagreement_penalty, 2),
        0.1
    )

    return {
        "verdict": final_verdict,
        "confidence": final_confidence
    }
