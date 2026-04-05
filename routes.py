import os
import uuid
import asyncio
import tempfile
import time
from fastapi import APIRouter, UploadFile, File, Request
from deep_translator import GoogleTranslator
import numpy as np

from models.request_models import ClaimRequest, TranslateReportRequest
from models.response_models import ClaimResponse
from pipeline.claim_pipeline import ClaimPipeline
from pipeline.document_pipeline import DocumentPipeline
from ingestion.ocr import choose_best_ocr_result
from progress_tracker import progress_tracker

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


def _warmup_ocr():
    sample = np.full((48, 240, 3), 255, dtype=np.uint8)
    lang = os.getenv("OCR_IMAGE_LANGS", "eng+tel+hin+tam+kan+mal").strip() or "eng"
    config = os.getenv("OCR_IMAGE_CONFIG", "--oem 3 --psm 6").strip() or "--oem 3 --psm 6"
    choose_best_ocr_result(image_bgr=sample, lang=lang, config=config)


def _warmup_pipelines_sync():
    claim_pipeline = get_claim_pipeline()
    document_pipeline = get_document_pipeline()
    document_claim_pipeline = document_pipeline.claim_pipeline

    _ = claim_pipeline.relevance_scorer
    _ = claim_pipeline.stance
    if claim_pipeline.enable_verifier_v2:
        _ = claim_pipeline.verifier_v2
    if claim_pipeline.enable_llm_verifier:
        _ = claim_pipeline.llm_verifier
    if claim_pipeline.enable_retrieval_v2:
        _ = claim_pipeline.retrieval_v2

    _ = document_claim_pipeline.relevance_scorer
    _ = document_claim_pipeline.stance
    if document_claim_pipeline.enable_verifier_v2:
        _ = document_claim_pipeline.verifier_v2
    if document_claim_pipeline.enable_llm_verifier:
        _ = document_claim_pipeline.llm_verifier
    if document_claim_pipeline.enable_retrieval_v2:
        _ = document_claim_pipeline.retrieval_v2

    # Warm OCR once so the first image/PDF request doesn't pay init cost.
    _warmup_ocr()

    return {
        "claim_pipeline_ready": True,
        "document_pipeline_ready": document_pipeline is not None,
        "ocr_ready": True,
    }


async def warmup_pipelines():
    return await asyncio.to_thread(_warmup_pipelines_sync)


async def run_with_disconnect_cancel(request: Request, coro_factory):
    cancel_event = asyncio.Event()
    work_task = asyncio.create_task(coro_factory(cancel_event))

    async def watch_disconnect():
        while not work_task.done():
            if await request.is_disconnected():
                cancel_event.set()
                work_task.cancel()
                return
            await asyncio.sleep(0.2)

    disconnect_task = asyncio.create_task(watch_disconnect())
    try:
        return await work_task
    finally:
        disconnect_task.cancel()
        try:
            await disconnect_task
        except asyncio.CancelledError:
            pass


def _progress_id_from_request(request: Request):
    return (request.headers.get("x-progress-id") or str(uuid.uuid4())).strip()


def _emit_progress(progress_id, **event):
    progress_tracker.emit(progress_id, **event)


@router.get("/progress/{progress_id}")
async def get_progress(progress_id: str):
    payload = progress_tracker.get(progress_id)
    if not payload:
        return {"error": "Progress not found"}
    return payload


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
async def check_claim(data: ClaimRequest, request: Request):
    progress_id = _progress_id_from_request(request)
    preview = (data.claim or "").strip()[:240]
    progress_tracker.start(progress_id, "claim", preview=preview)
    try:
        result = await run_with_disconnect_cancel(
            request,
            lambda cancel_event: get_claim_pipeline().run(
                data.claim,
                cancel_event=cancel_event,
                progress_callback=lambda event: _emit_progress(progress_id, **event),
            ),
        )
        if isinstance(result, dict):
            result["progress_id"] = progress_id
        progress_tracker.complete(progress_id, detail="Claim analysis complete")
        return result
    except asyncio.CancelledError:
        progress_tracker.cancel(progress_id, detail="Claim analysis cancelled")
        return {"error": "Request cancelled by client."}
    except Exception as exc:
        progress_tracker.error(progress_id, detail=str(exc))
        raise

@router.post("/analyze_pdf")
async def analyze_pdf(request: Request, file: UploadFile = File(...)):
    route_start = time.time()
    progress_id = _progress_id_from_request(request)

    if not file.filename.endswith(".pdf"):
        return {"error": "Only PDF files allowed"}

    temp_filename = None
    progress_tracker.start(progress_id, "pdf", preview=file.filename or "PDF upload")
    progress_tracker.emit(progress_id, stage="input", status="done", detail="PDF uploaded")

    try:
        save_start = time.time()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
            temp_filename = f.name
            f.write(await file.read())
        print("Route /analyze_pdf save upload:", round(time.time() - save_start, 3), "sec")

        try:
            result = await run_with_disconnect_cancel(
                request,
                lambda cancel_event: get_document_pipeline().process_pdf(
                    temp_filename,
                    cancel_event=cancel_event,
                    progress_callback=lambda event: _emit_progress(progress_id, **event),
                ),
            )
            print("Route /analyze_pdf total:", round(time.time() - route_start, 3), "sec")
            if isinstance(result, dict):
                result["progress_id"] = progress_id
            progress_tracker.complete(progress_id, detail="PDF analysis complete")
            return result
        except asyncio.CancelledError:
            progress_tracker.cancel(progress_id, detail="PDF analysis cancelled")
            return {"error": "Request cancelled by client."}
        except Exception as exc:
            progress_tracker.error(progress_id, detail=str(exc))
            raise
    finally:
        if temp_filename and os.path.exists(temp_filename):
            os.remove(temp_filename)


@router.post("/analyze_image")
async def analyze_image(request: Request, file: UploadFile = File(...)):
    route_start = time.time()
    progress_id = _progress_id_from_request(request)

    if not file.filename.lower().endswith((".png", ".jpg", ".jpeg")):
        return {"error": "Only image files allowed"}

    temp_filename = None
    progress_tracker.start(progress_id, "image", preview=file.filename or "Image upload")
    progress_tracker.emit(progress_id, stage="input", status="done", detail="Image uploaded")

    try:
        suffix = os.path.splitext(file.filename or "")[1].lower() or ".png"
        save_start = time.time()
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
            temp_filename = f.name
            f.write(await file.read())
        print("Route /analyze_image save upload:", round(time.time() - save_start, 3), "sec")

        try:
            result = await run_with_disconnect_cancel(
                request,
                lambda cancel_event: get_document_pipeline().process_image(
                    temp_filename,
                    cancel_event=cancel_event,
                    progress_callback=lambda event: _emit_progress(progress_id, **event),
                ),
            )
            print("Route /analyze_image total:", round(time.time() - route_start, 3), "sec")
            if isinstance(result, dict):
                result["progress_id"] = progress_id
            progress_tracker.complete(progress_id, detail="Image analysis complete")
            return result
        except asyncio.CancelledError:
            progress_tracker.cancel(progress_id, detail="Image analysis cancelled")
            return {"error": "Request cancelled by client."}
        except Exception as exc:
            progress_tracker.error(progress_id, detail=str(exc))
            raise
    finally:
        if temp_filename and os.path.exists(temp_filename):
            os.remove(temp_filename)


@router.post("/translate_report")
async def translate_report(data: TranslateReportRequest):
    target = (data.target_lang or "en").strip().lower()

    try:
        translator = GoogleTranslator(source="auto", target=target)
        translated = _translate_value(data.report, translator)
        return {"report": translated, "target_lang": target}
    except Exception as e:
        return {"error": f"Translation failed: {e}"}
