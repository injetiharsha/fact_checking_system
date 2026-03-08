# ingestion/pdf.py

import PyPDF2
import pdfplumber
import pytesseract
import pypdfium2 as pdfium


def extract_pdf(path: str) -> str:
    chunks = []

    try:
        # First pass: pdfplumber generally extracts text more reliably.
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                extracted = page.extract_text() or ""
                if extracted.strip():
                    chunks.append(extracted.strip())
    except Exception as e:
        print(f"PDF extraction (pdfplumber) error: {e}")

    # Fallback pass: PyPDF2.
    if not chunks:
        try:
            with open(path, "rb") as file:
                reader = PyPDF2.PdfReader(file)
                for page in reader.pages:
                    extracted = page.extract_text() or ""
                    if extracted.strip():
                        chunks.append(extracted.strip())
        except Exception as e:
            print(f"PDF extraction (PyPDF2) error: {e}")

    # OCR fallback for scanned/image PDFs.
    if not chunks:
        try:
            pdf = pdfium.PdfDocument(path)
            max_pages = min(len(pdf), 20)

            for i in range(max_pages):
                page = pdf[i]
                bitmap = page.render(scale=2.0)
                image = bitmap.to_pil()
                extracted = pytesseract.image_to_string(image) or ""
                if extracted.strip():
                    chunks.append(extracted.strip())
        except Exception as e:
            print(f"PDF extraction (OCR fallback) error: {e}")

    return "\n".join(chunks).strip()
