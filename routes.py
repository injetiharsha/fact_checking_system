import os
import uuid
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
    return await claim_pipeline.run(data.claim)



@router.post("/analyze_url")
def analyze_url(data: URLRequest):
    return document_pipeline.run(data.url)


@router.post("/analyze_pdf")
async def analyze_pdf(file: UploadFile = File(...)):

    if not file.filename.endswith(".pdf"):
        return {"error": "Only PDF files allowed"}

    temp_filename = f"temp_{uuid.uuid4()}.pdf"

    with open(temp_filename, "wb") as f:
        f.write(await file.read())

    result = document_pipeline.process_pdf(temp_filename)

    os.remove(temp_filename)

    return result


@router.post("/analyze_image")
async def analyze_image(file: UploadFile = File(...)):

    if not file.filename.lower().endswith((".png", ".jpg", ".jpeg")):
        return {"error": "Only image files allowed"}

    temp_filename = f"temp_{uuid.uuid4()}.png"

    with open(temp_filename, "wb") as f:
        f.write(await file.read())

    result = document_pipeline.process_image(temp_filename)

    os.remove(temp_filename)

    return result
