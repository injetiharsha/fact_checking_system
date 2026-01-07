from functools import lru_cache
from deep_translator import GoogleTranslator
from app.nlp.language import detect_language


_translator = GoogleTranslator(source="auto", target="en")


@lru_cache(maxsize=1000)
def _cached_translate(text: str) -> str:
    return _translator.translate(text)


def translate_to_english(text: str) -> str:
    if not text:
        return text

    lang = detect_language(text)

    if lang in ("en", "unknown"):
        return text

    try:
        return _cached_translate(text)
    except Exception:
        return text
