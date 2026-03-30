import os
import uuid
import asyncio
import tempfile
from fastapi import APIRouter, UploadFile, File
from deep_translator import GoogleTranslator

from models.request_models import ClaimRequest, URLRequest, TranslateReportRequest
from models.response_models import ClaimResponse
from pipeline.claim_pipeline import ClaimPipeline
from pipeline.document_pipeline import DocumentPipeline

router = APIRouter()

_claim_pipeline = None
_document_pipeline = None


def get_claim_pipeline():
    global _claim_pipeline
    if _claim_pipeline is None:
        _claim_pipeline = ClaimPipeline()
    return _claim_pipeline


def get_document_pipeline():
    global _document_pipeline
    if _document_pipeline is None:
        _document_pipeline = DocumentPipeline()
    return _document_pipeline


def _translate_value(value, translator):
    language_keys = {"language", "target_lang", "source_lang"}
    if isinstance(value, str):
        if value.startswith("http://") or value.startswith("https://"):
            return value
        stripped = value.strip()
        if not stripped:
            return value
        # Keep language codes stable (en, hi, ta, etc.)
        if len(stripped) <= 5 and stripped.replace("-", "").isalpha() and stripped.lower() == stripped:
            return value
        try:
            return translator.translate(value)
        except Exception:
            return value
    if isinstance(value, list):
        return [_translate_value(v, translator) for v in value]
    if isinstance(value, dict):
        translated = {}
        for k, v in value.items():
            if k in language_keys:
                translated[k] = v
            else:
                translated[k] = _translate_value(v, translator)
        return translated
    return value


@router.post("/check")
async def check_claim(data: ClaimRequest):
    try:
        return await get_claim_pipeline().run(data.claim)
    except asyncio.CancelledError:
        return {"error": "Request cancelled during server reload/shutdown. Please retry."}



@router.post("/analyze_url")
async def analyze_url(data: URLRequest):
    try:
        return await get_document_pipeline().run(data.url)
    except asyncio.CancelledError:
        return {"error": "Request cancelled during server reload/shutdown. Please retry."}


@router.post("/analyze_pdf")
async def analyze_pdf(file: UploadFile = File(...)):

    if not file.filename.endswith(".pdf"):
        return {"error": "Only PDF files allowed"}

    temp_filename = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
            temp_filename = f.name
            f.write(await file.read())

        try:
            return await get_document_pipeline().process_pdf(temp_filename)
        except asyncio.CancelledError:
            return {"error": "Request cancelled during server reload/shutdown. Please retry."}
    finally:
        if temp_filename and os.path.exists(temp_filename):
            os.remove(temp_filename)


@router.post("/analyze_image")
async def analyze_image(file: UploadFile = File(...)):

    if not file.filename.lower().endswith((".png", ".jpg", ".jpeg")):
        return {"error": "Only image files allowed"}

    temp_filename = None

    try:
        suffix = os.path.splitext(file.filename or "")[1].lower() or ".png"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
            temp_filename = f.name
            f.write(await file.read())

        try:
            return await get_document_pipeline().process_image(temp_filename)
        except asyncio.CancelledError:
            return {"error": "Request cancelled during server reload/shutdown. Please retry."}
    finally:
        if temp_filename and os.path.exists(temp_filename):
            os.remove(temp_filename)


@router.post("/translate_report")
async def translate_report(data: TranslateReportRequest):
    target = (data.target_lang or "en").strip().lower()
    if target in {"en", "english"}:
        return {"report": data.report, "target_lang": "en"}

    try:
        translator = GoogleTranslator(source="auto", target=target)
        translated = _translate_value(data.report, translator)
        return {"report": translated, "target_lang": target}
    except Exception as e:
        return {"error": f"Translation failed: {e}"}
