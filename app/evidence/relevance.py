from app.nlp.language import detect_language
from app.nlp.translate import translate_to_english

def normalize_text(text: str):
    lang = detect_language(text)
    if lang != "en":
        text = translate_to_english(text)
    return text.lower()

def is_relevant(claim: str, text: str, min_overlap=3):
    claim = normalize_text(claim)
    text = normalize_text(text)

    claim_words = set(claim.split())
    text_words = set(text.split())

    overlap = len(claim_words & text_words)
    return overlap >= min_overlap
