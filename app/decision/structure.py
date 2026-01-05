def validate_claim(text: str):
    """
    Checks whether the input is a factual claim.
    """
    if len(text.split()) < 3:
        return "UNCERTAIN", "Claim too short"

    if text.strip().endswith("?"):
        return "UNCERTAIN", "Question, not a claim"

    opinion_words = ["i think", "i believe", "in my opinion"]
    for w in opinion_words:
        if w in text.lower():
            return "UNCERTAIN", "Opinion detected"

    return None, None
