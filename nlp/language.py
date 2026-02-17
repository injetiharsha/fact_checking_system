# nlp/language.py

from langdetect import detect, LangDetectException


def detect_language(text: str) -> str:
    """
    Detect language of input text.
    Returns ISO 639-1 language code (e.g., 'en', 'hi', 'ta').
    """

    try:
        language = detect(text)
        return language
    except LangDetectException:
        return "unknown"
