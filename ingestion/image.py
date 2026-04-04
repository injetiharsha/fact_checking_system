# ingestion/image.py

import os

import cv2
from ingestion.ocr import choose_best_ocr_result


# If Windows and not in PATH, uncomment:
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def extract_image_text(path: str) -> dict:
    try:
        if not os.path.exists(path):
            return {"text": "", "usable": False, "reason": "file_missing", "avg_confidence": 0.0}

        image = cv2.imread(path)
        if image is None:
            return {"text": "", "usable": False, "reason": "image_open_failed", "avg_confidence": 0.0}

        lang = os.getenv("OCR_IMAGE_LANGS", "eng+tel+hin+tam+kan+mal").strip() or "eng"
        config = os.getenv("OCR_IMAGE_CONFIG", "--oem 3 --psm 6").strip() or "--oem 3 --psm 6"

        best = choose_best_ocr_result(image_bgr=image, lang=lang, config=config)
        if not best:
            return {"text": "", "usable": False, "reason": "ocr_failed", "avg_confidence": 0.0}

        return {
            "text": best["text"].strip(),
            "usable": bool(best["usable"]),
            "reason": best["reason"],
            "avg_confidence": best["avg_confidence"],
            "word_count": best["word_count"],
            "script_ratio": best["script_ratio"],
            "ocr_langs": lang,
        }

    except Exception as e:
        print(f"OCR extraction error: {e}")
        return {"text": "", "usable": False, "reason": "ocr_exception", "avg_confidence": 0.0}
