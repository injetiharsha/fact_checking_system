# models/response_models.py

from pydantic import BaseModel
from typing import List

class EvidenceItem(BaseModel):
    source: str
    url: str
    text: str
    weight: float
    stance: str
    confidence: float


class ClaimResponse(BaseModel):
    claim: str
    evidence: List[EvidenceItem]
    final_verdict: str
    confidence: float
    citations: List[str]
    explanation: str
