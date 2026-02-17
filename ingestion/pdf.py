# ingestion/pdf.py

import PyPDF2


def extract_pdf(path: str) -> str:
    text = ""

    try:
        with open(path, "rb") as file:
            reader = PyPDF2.PdfReader(file)

            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"

    except Exception as e:
        print(f"PDF extraction error: {e}")

    return text.strip()
