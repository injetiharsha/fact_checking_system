from pydantic import BaseModel
from typing import List, Dict, Any


class EvidenceItem(BaseModel):
    source: str
    url: str
    text: str
    weight: float
    stance: str
    confidence: float


class ClaimResponse(BaseModel):
    claim: str
    language: str
    evidence: List[EvidenceItem]
    final_verdict: str
    confidence: float
    conflict_analysis: str
    citations: List[str]
    logical_analysis: Dict[str, Any]
    explanation: str
