from langdetect import detect, DetectorFactory

DetectorFactory.seed = 0  # make detection deterministic


def detect_language(text: str) -> str:
    if not text or len(text.strip()) < 20:
        return "unknown"

    try:
        return detect(text)
    except Exception:
        return "unknown"
