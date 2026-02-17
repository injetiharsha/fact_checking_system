# ingestion/router.py

from ingestion.webpage import fetch_webpage
from ingestion.pdf import extract_pdf
from ingestion.image import extract_image_text


def ingest(source: str):

    if source.lower().endswith(".pdf"):
        return extract_pdf(source)

    if source.lower().endswith((".jpg", ".jpeg", ".png")):
        return extract_image_text(source)

    return fetch_webpage(source)
