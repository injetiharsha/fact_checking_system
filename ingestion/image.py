# ingestion/image.py

import pytesseract
from PIL import Image
import os


# If Windows and not in PATH, uncomment:
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def extract_image_text(path: str) -> str:
    try:
        if not os.path.exists(path):
            return ""

        image = Image.open(path)
        text = pytesseract.image_to_string(image)

        return text.strip()

    except Exception as e:
        print(f"OCR extraction error: {e}")
        return ""
