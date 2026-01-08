from fastapi import APIRouter, UploadFile, File
import tempfile
import os

from app.evidence.ocr import extract_text_from_image
from app.evidence.fetcher import fact_check_pipeline

router = APIRouter()

@router.post("/check")
async def check(payload: ClaimRequest):
    claim = payload.claim.strip()

    if not claim:
        return {"error": "Empty claim"}

    return await fact_check_pipeline(claim)



@router.post("/check/image")
async def check_image(file: UploadFile = File(...)):
    suffix = os.path.splitext(file.filename)[1]

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        text = extract_text_from_image(tmp_path)
        if not text:
            return {"error": "No text detected in image"}

        return await fact_check_pipeline(text)

    finally:
        os.remove(tmp_path)
