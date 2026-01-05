from fastapi import APIRouter, UploadFile, File
import os, shutil, asyncio
from app.ml.preprocess import clean_text
from app.ml.inference import run_inference
from app.evidence.fetcher import fetch_wikipedia_evidence_async, fetch_web_evidence
from app.evidence.similarity import similarity_score
from app.decision.verdict import final_verdict
from app.evidence.ocr import extract_text_from_image
from app.core.logger import now_ms




router = APIRouter()

@router.post("/check")
async def check_claim(data: dict):
    raw_text = data.get("text", "")
    cleaned_text = clean_text(raw_text)

    if not cleaned_text:
        return {"error": "Invalid input"}

    # ML inference
    ml_result = run_inference(cleaned_text)

    # Evidence fetching
    evidence = await fetch_wikipedia_evidence_async(cleaned_text)

    web_evidence = fetch_web_evidence(cleaned_text)
    evidence.extend(web_evidence)



    scores = []
    for item in evidence:
        score = similarity_score(cleaned_text, item["text"])
        scores.append(score)

    # Final decision
    verdict = final_verdict(
    ml_result["label"],
    ml_result["confidence"],
    scores,
    cleaned_text
)


    return {
        "claim": raw_text,
        "ml_verdict": ml_result,
        "evidence": evidence,
        "decision": verdict
    }

@router.post("/check/image")
async def check_image(file: UploadFile = File(...)):
    temp_path = f"temp_{file.filename}"

    # save image temporarily
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # OCR
    extracted_text = extract_text_from_image(temp_path)

    # cleanup
    os.remove(temp_path)

    if not extracted_text:
        return {"error": "No text detected in image"}

    cleaned_text = clean_text(extracted_text)

    # ML inference
    ml_result = run_inference(cleaned_text)

    # Evidence
    evidence = await fetch_wikipedia_evidence_async(cleaned_text)


    scores = []
    for item in evidence:
        scores.append(similarity_score(cleaned_text, item["text"]))

    decision = final_verdict(
    ml_result["label"],
    ml_result["confidence"],
    scores,
    cleaned_text
)



    return {
        "extracted_text": extracted_text,
        "ml_verdict": ml_result,
        "decision": decision,
        "evidence": evidence
    }

