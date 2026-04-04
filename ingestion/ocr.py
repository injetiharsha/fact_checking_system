import re

import cv2
import pytesseract
from pytesseract import Output


def preprocess_variants(image_bgr):
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    upscaled = cv2.resize(gray, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    denoised = cv2.GaussianBlur(upscaled, (3, 3), 0)
    adaptive = cv2.adaptiveThreshold(
        denoised,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        11,
    )
    otsu = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    return [upscaled, adaptive, otsu]


def ocr_variant(image, lang, config):
    data = pytesseract.image_to_data(image, lang=lang, config=config, output_type=Output.DICT)
    words = []
    confidences = []
    for text, conf in zip(data.get("text", []), data.get("conf", [])):
        token = (text or "").strip()
        if not token:
            continue
        words.append(token)
        try:
            value = float(conf)
        except Exception:
            value = -1.0
        if value >= 0:
            confidences.append(value)

    joined = " ".join(words).strip()
    avg_conf = round(sum(confidences) / len(confidences), 2) if confidences else 0.0
    return {
        "text": joined,
        "avg_confidence": avg_conf,
        "word_count": len(words),
    }


def text_quality(text):
    normalized = " ".join((text or "").split())
    if not normalized:
        return {
            "usable": False,
            "reason": "no_text",
            "script_ratio": 0.0,
            "word_count": 0,
        }

    word_count = len(normalized.split())
    alpha_chars = [ch for ch in normalized if ch.isalpha()]
    if not alpha_chars:
        return {
            "usable": False,
            "reason": "no_letters",
            "script_ratio": 0.0,
            "word_count": word_count,
        }

    indic_chars = 0
    for ch in alpha_chars:
        code = ord(ch)
        if (
            0x0900 <= code <= 0x097F
            or 0x0C00 <= code <= 0x0C7F
            or 0x0B80 <= code <= 0x0BFF
            or 0x0C80 <= code <= 0x0CFF
            or 0x0D00 <= code <= 0x0D7F
        ):
            indic_chars += 1

    script_ratio = indic_chars / max(len(alpha_chars), 1)
    suspicious_ascii = len(re.findall(r"\b[a-z]{1,3}\b", normalized.lower()))
    long_words = len([w for w in normalized.split() if len(w) >= 4])

    usable = word_count >= 6 and long_words >= 3 and suspicious_ascii <= max(5, word_count // 2)
    reason = "ok" if usable else "low_quality_text"
    return {
        "usable": usable,
        "reason": reason,
        "script_ratio": round(script_ratio, 3),
        "word_count": word_count,
    }


def score_ocr_candidate(result, position_weight=0.0):
    return (
        result["avg_confidence"] * 0.7
        + min(result["word_count"], 40) * 0.6
        + result["script_ratio"] * 25
        + (18.0 if result.get("usable") else 0.0)
        + position_weight
    )


def choose_best_ocr_result(image_bgr, lang, config, variant_images=None, base_position_weight=0.0):
    candidates = []
    variants = variant_images if variant_images is not None else preprocess_variants(image_bgr)
    for variant_idx, variant in enumerate(variants):
        result = ocr_variant(variant, lang=lang, config=config)
        quality = text_quality(result["text"])
        result.update(quality)
        result["score"] = score_ocr_candidate(
            result,
            position_weight=max(base_position_weight - (variant_idx * 0.15), 0.0),
        )
        candidates.append(result)

    return max(candidates, key=lambda item: item["score"], default=None)
