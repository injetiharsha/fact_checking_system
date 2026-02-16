from fastapi import APIRouter
from models.request_models import ClaimRequest, URLRequest
from models.response_models import ClaimResponse
from pipeline.claim_pipeline import ClaimPipeline
from pipeline.document_pipeline import DocumentPipeline

router = APIRouter()

claim_pipeline = ClaimPipeline()
document_pipeline = DocumentPipeline()


@router.post("/check", response_model=ClaimResponse)
def check_claim(data: ClaimRequest):
    return claim_pipeline.run(data.claim)


@router.post("/analyze_url")
def analyze_url(data: URLRequest):
    return document_pipeline.run(data.url)
