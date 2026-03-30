# nlp/language.py

import re

from langdetect import LangDetectException, detect


ENGLISH_FUNCTION_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "born",
    "by",
    "can",
    "for",
    "from",
    "has",
    "have",
    "in",
    "is",
    "it",
    "of",
    "on",
    "the",
    "to",
    "was",
    "were",
    "with",
}


def _looks_like_english_ascii(text: str) -> bool:
    stripped = (text or "").strip()
    if not stripped:
        return False

    if any(ord(ch) > 127 for ch in stripped):
        return False

    tokens = re.findall(r"[A-Za-z']+", stripped.lower())
    if len(tokens) < 3:
        return False

    english_hits = sum(1 for token in tokens if token in ENGLISH_FUNCTION_WORDS)
    alpha_chars = sum(1 for ch in stripped if ch.isalpha())
    ascii_alpha_chars = sum(1 for ch in stripped if ch.isascii() and ch.isalpha())
    mostly_ascii_alpha = alpha_chars == 0 or (ascii_alpha_chars / max(alpha_chars, 1)) > 0.95
    return mostly_ascii_alpha and english_hits >= 1


def detect_language(text: str) -> str:
    """
    Detect language of input text.
    Returns ISO 639-1 language code (e.g., 'en', 'hi', 'ta').
    """

    if _looks_like_english_ascii(text):
        return "en"

    try:
        language = detect(text)
        if language != "en" and _looks_like_english_ascii(text):
            return "en"
        return language
    except LangDetectException:
        return "en" if _looks_like_english_ascii(text) else "unknown"
