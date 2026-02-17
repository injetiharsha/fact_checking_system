# nlp/translate.py

from deep_translator import GoogleTranslator


def translate_to_english(text: str, source_lang: str) -> str:
    """
    Translate text to English if not already English.
    """

    if source_lang == "en" or source_lang == "unknown":
        return text

    try:
        translated = GoogleTranslator(
            source=source_lang,
            target="en"
        ).translate(text)

        return translated

    except Exception:
        # Fallback if translation fails
        return text
