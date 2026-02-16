from pydantic import BaseModel

class ClaimRequest(BaseModel):
    claim: str


class URLRequest(BaseModel):
    url: str
