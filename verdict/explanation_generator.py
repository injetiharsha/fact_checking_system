# verdict/explanation_generator.py

def generate_explanation(claim, evidence_list, verdict, confidence):
    support_sources = []
    refute_sources = []

    for ev in evidence_list:
        if ev["stance"] == "SUPPORT":
            support_sources.append(ev["source"])
        elif ev["stance"] == "REFUTE":
            refute_sources.append(ev["source"])

    explanation = f'Claim: "{claim}"\n\n'

    explanation += f"Verdict: {verdict}\n"
    explanation += f"Confidence: {round(confidence*100, 2)}%\n\n"

    if verdict == "TRUE":
        explanation += (
            f"Multiple high-credibility sources including "
            f"{', '.join(support_sources)} support the claim. "
            f"No strong contradictory evidence was found."
        )

    elif verdict == "FALSE":
        explanation += (
            f"Credible sources including "
            f"{', '.join(refute_sources)} contradict the claim. "
            f"The supporting evidence is weak or unreliable."
        )

    else:
        explanation += (
            "The available evidence is mixed or insufficient "
            "to confidently verify the claim."
        )

    return explanation
