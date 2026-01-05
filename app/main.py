from fastapi import FastAPI
from app.routes import router

app = FastAPI(title="Fact Checking System")

app.include_router(router)

@app.get("/")
def health():
    return {"status": "running"}
