import re

def clean_text(text: str) -> str:
    """
    Basic text normalization for fact checking.
    """

    if not isinstance(text, str):
        return ""

    # lowercase
    text = text.lower()

    # remove urls
    text = re.sub(r"http\S+|www\S+", "", text)

    # remove special characters
    text = re.sub(r"[^a-z0-9\s]", "", text)

    # collapse multiple spaces
    text = re.sub(r"\s+", " ", text)

    return text.strip()
