from pydantic import BaseModel
from typing import Any, Dict

class ClaimRequest(BaseModel):
    claim: str


class TranslateReportRequest(BaseModel):
    report: Dict[str, Any]
    target_lang: str
