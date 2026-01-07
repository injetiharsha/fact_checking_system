from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # for development
    allow_credentials=True,
    allow_methods=["*"],      # allows OPTIONS
    allow_headers=["*"],
)

app.include_router(router)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/")
def root():
    return {
        "message": "Fact Checking API is running",
        "endpoints": ["/check", "/check/image", "/health"]
    }

