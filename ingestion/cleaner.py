# ingestion/cleaner.py

import re


def clean_text(text: str) -> str:
    """
    Basic text cleaning:
    - Remove extra spaces
    - Remove weird characters
    - Normalize quotes
    """

    if not text:
        return ""

    # Remove multiple spaces
    text = re.sub(r"\s+", " ", text)

    # Remove non-printable characters
    text = re.sub(r"[^\x00-\x7F]+", " ", text)

    # Normalize quotes
    text = text.replace("“", '"').replace("”", '"')
    text = text.replace("’", "'")

    return text.strip()
