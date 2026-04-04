import os

import cv2
import numpy as np
import PyPDF2
import pdfplumber
import pypdfium2 as pdfium

from ingestion.ocr import choose_best_ocr_result


def _env_int(name: str, default: int) -> int:
    try:
        return max(1, int(os.getenv(name, str(default)).strip()))
    except Exception:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return max(0.5, float(os.getenv(name, str(default)).strip()))
    except Exception:
        return default


def _extract_text_layer(path: str):
    chunks = []
    pages = []
    source = None

    try:
        with pdfplumber.open(path) as pdf:
            for page_number, page in enumerate(pdf.pages, start=1):
                extracted = page.extract_text() or ""
                image_count = len(page.images)
                if extracted.strip():
                    cleaned = extracted.strip()
                    chunks.append(cleaned)
                    pages.append({
                        "page_number": page_number,
                        "text": cleaned,
                        "source": "pdfplumber",
                        "image_count": image_count,
                        "word_count": len(cleaned.split()),
                        "text_chars": len(cleaned),
                    })
        if chunks:
            source = "pdfplumber"
    except Exception as e:
        print(f"PDF extraction (pdfplumber) error: {e}")

    if not chunks:
        try:
            with open(path, "rb") as file:
                reader = PyPDF2.PdfReader(file)
                for page_number, page in enumerate(reader.pages, start=1):
                    extracted = page.extract_text() or ""
                    image_count = 0
                    if extracted.strip():
                        cleaned = extracted.strip()
                        chunks.append(cleaned)
                        pages.append({
                            "page_number": page_number,
                            "text": cleaned,
                            "source": "pypdf2",
                            "image_count": image_count,
                            "word_count": len(cleaned.split()),
                            "text_chars": len(cleaned),
                        })
            if chunks:
                source = "pypdf2"
        except Exception as e:
            print(f"PDF extraction (PyPDF2) error: {e}")

    return chunks, pages, source


def _ocr_pdf_pages(path: str) -> dict:
    lang = os.getenv("OCR_PDF_LANGS", os.getenv("OCR_IMAGE_LANGS", "eng")).strip() or "eng"
    config = os.getenv("OCR_PDF_CONFIG", os.getenv("OCR_IMAGE_CONFIG", "--oem 3 --psm 6")).strip() or "--oem 3 --psm 6"
    render_scale = _env_float("OCR_PDF_RENDER_SCALE", 2.5)
    max_pages = _env_int("OCR_PDF_MAX_PAGES", 20)

    try:
        pdf = pdfium.PdfDocument(path)
        page_count = len(pdf)
        pages_to_scan = min(page_count, max_pages)
        page_results = []

        for i in range(pages_to_scan):
            page = pdf[i]
            bitmap = page.render(scale=render_scale)
            image = bitmap.to_pil()
            image_bgr = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            best = choose_best_ocr_result(
                image_bgr=image_bgr,
                lang=lang,
                config=config,
                base_position_weight=max(1.5 - (i * 0.08), 0.0),
            )
            if best and (best.get("text") or "").strip():
                best["page_number"] = i + 1
                page_results.append(best)

        if not page_results:
            return {
                "text": "",
                "pages": [],
                "usable": False,
                "reason": "ocr_failed",
                "avg_confidence": 0.0,
                "word_count": 0,
                "script_ratio": 0.0,
                "ocr_langs": lang,
                "ocr_pages_scanned": pages_to_scan,
                "ocr_page_count": page_count,
            }

        text_chunks = [item["text"].strip() for item in page_results if item["text"].strip()]
        usable_pages = [item for item in page_results if item.get("usable")]
        avg_confidence = round(
            sum(item.get("avg_confidence", 0.0) for item in page_results) / len(page_results),
            2,
        )
        avg_script_ratio = round(
            sum(item.get("script_ratio", 0.0) for item in page_results) / len(page_results),
            3,
        )

        return {
            "text": "\n".join(text_chunks).strip(),
            "pages": [
                {
                    "page_number": item.get("page_number"),
                    "text": item.get("text", "").strip(),
                    "source": "ocr",
                    "usable": bool(item.get("usable")),
                    "avg_confidence": item.get("avg_confidence", 0.0),
                    "word_count": item.get("word_count", 0),
                    "script_ratio": item.get("script_ratio", 0.0),
                    "reason": item.get("reason"),
                    "image_count": item.get("image_count", 0),
                    "text_chars": len(item.get("text", "").strip()),
                }
                for item in page_results
                if (item.get("text") or "").strip()
            ],
            "usable": bool(usable_pages),
            "reason": "ok" if usable_pages else "low_quality_text",
            "avg_confidence": avg_confidence,
            "word_count": sum(item.get("word_count", 0) for item in page_results),
            "script_ratio": avg_script_ratio,
            "ocr_langs": lang,
            "ocr_pages_scanned": pages_to_scan,
            "ocr_page_count": page_count,
            "usable_page_count": len(usable_pages),
        }
    except Exception as e:
        print(f"PDF extraction (OCR fallback) error: {e}")
        return {
            "text": "",
            "usable": False,
            "reason": "ocr_exception",
            "avg_confidence": 0.0,
            "word_count": 0,
            "script_ratio": 0.0,
            "ocr_langs": lang,
        }


def extract_pdf_with_details(path: str) -> dict:
    chunks, pages, source = _extract_text_layer(path)
    if chunks:
        text = "\n".join(chunks).strip()
        return {
            "text": text,
            "pages": pages,
            "ocr_details": None,
            "extraction_source": source,
        }

    ocr_result = _ocr_pdf_pages(path)
    return {
        "text": (ocr_result or {}).get("text", "").strip(),
        "pages": (ocr_result or {}).get("pages", []),
        "ocr_details": ocr_result,
        "extraction_source": "ocr",
    }


def extract_pdf(path: str) -> str:
    return extract_pdf_with_details(path)["text"]
