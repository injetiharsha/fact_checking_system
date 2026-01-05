from fastapi import APIRouter

router = APIRouter()

@router.post("/check")
def check(data: dict):
    return {
        "input": data["text"],
        "status": "pipeline not active yet"
    }
