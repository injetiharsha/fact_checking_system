def build_explanation(verdict, stances):
    if not stances:
        return "No reliable external evidence was found to verify this claim."

    support = [s for s in stances if s["label"] == "supports"]
    contradict = [s for s in stances if s["label"] == "contradicts"]

    if verdict == "TRUE":
        return f"Multiple independent sources support the claim ({len(support)} confirmations)."

    if verdict == "FALSE":
        return f"Multiple independent sources contradict the claim ({len(contradict)} contradictions)."

    if verdict == "PARTIALLY TRUE":
        return "Some sources support the claim while others contradict it."

    return "Available sources do not provide enough information to verify this claim."
