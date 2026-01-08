from pydantic import BaseModel, Field

class ClaimRequest(BaseModel):
    claim: str = Field(..., min_length=3)
