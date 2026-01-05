def hard_fact_check(text: str):
    text = text.lower()

    # Geography
    if "india" in text and "europe" in text:
        return "FAKE", "India is in Asia"

    if "sun" in text and "revolves around earth" in text:
        return "FAKE", "Heliocentric model violation"

    # Science
    if "earth" in text and "flat" in text:
        return "FAKE", "Earth is spherical"

    # Time travel (basic)
    if "travel back in time" in text:
        return "UNCERTAIN", "Speculative physics"

    return None, None
