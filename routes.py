import os
import uuid
import asyncio
from fastapi import APIRouter, UploadFile, File

from models.request_models import ClaimRequest, URLRequest
from models.response_models import ClaimResponse
from pipeline.claim_pipeline import ClaimPipeline
from pipeline.document_pipeline import DocumentPipeline

router = APIRouter()

claim_pipeline = ClaimPipeline()
document_pipeline = DocumentPipeline()


@router.post("/check")
async def check_claim(data: ClaimRequest):
    try:
        return await claim_pipeline.run(data.claim)
    except asyncio.CancelledError:
        return {"error": "Request cancelled during server reload/shutdown. Please retry."}



@router.post("/analyze_url")
async def analyze_url(data: URLRequest):
    try:
        return await document_pipeline.run(data.url)
    except asyncio.CancelledError:
        return {"error": "Request cancelled during server reload/shutdown. Please retry."}


@router.post("/analyze_pdf")
async def analyze_pdf(file: UploadFile = File(...)):

    if not file.filename.endswith(".pdf"):
        return {"error": "Only PDF files allowed"}

    temp_filename = f"temp_{uuid.uuid4()}.pdf"

    try:
        with open(temp_filename, "wb") as f:
            f.write(await file.read())

        try:
            return await document_pipeline.process_pdf(temp_filename)
        except asyncio.CancelledError:
            return {"error": "Request cancelled during server reload/shutdown. Please retry."}
    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)


@router.post("/analyze_image")
async def analyze_image(file: UploadFile = File(...)):

    if not file.filename.lower().endswith((".png", ".jpg", ".jpeg")):
        return {"error": "Only image files allowed"}

    temp_filename = f"temp_{uuid.uuid4()}.png"

    try:
        with open(temp_filename, "wb") as f:
            f.write(await file.read())

        try:
            return await document_pipeline.process_image(temp_filename)
        except asyncio.CancelledError:
            return {"error": "Request cancelled during server reload/shutdown. Please retry."}
    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
