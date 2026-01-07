import pytesseract
import cv2
import os


def _configure_tesseract():
    """
    Configure Tesseract path only if explicitly provided.
    """
    tesseract_cmd = os.getenv("TESSERACT_CMD")
    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd


_configured = False


def extract_text_from_image(image_path: str, lang: str = "eng") -> str:
    global _configured

    if not _configured:
        _configure_tesseract()
        _configured = True

    try:
        image = cv2.imread(image_path)
        if image is None:
            return ""

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        gray = cv2.threshold(
            gray, 0, 255,
            cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )[1]

        config = f"--oem 3 --psm 6 -l {lang}"

        text = pytesseract.image_to_string(
            gray,
            config=config
        )

        return text.strip()

    except Exception:
        return ""
