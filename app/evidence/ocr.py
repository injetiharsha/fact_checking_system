import pytesseract
from PIL import Image
import cv2
import numpy as np

# IMPORTANT: adjust if path differs
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def extract_text_from_image(image_path: str) -> str:
    """
    Robust OCR with preprocessing
    """
    try:
        # read image using OpenCV
        image = cv2.imread(image_path)

        if image is None:
            return ""

        # convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # increase contrast
        gray = cv2.threshold(
            gray, 0, 255,
            cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )[1]

        # OCR config
        custom_config = r"--oem 3 --psm 6"

        text = pytesseract.image_to_string(
            gray,
            config=custom_config
        )

        return text.strip()

    except Exception as e:
        print("OCR ERROR:", e)
        return ""
