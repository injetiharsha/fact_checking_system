import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load env first and force model caches to a writable local path.
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

is_vercel = os.getenv("VERCEL") == "1"
default_cache_dir = "/tmp/model_cache" if is_vercel else str(BASE_DIR / ".venv" / "model_cache")
model_cache_root = Path(os.getenv("MODEL_CACHE_DIR", default_cache_dir)).expanduser()

cache_paths = {
    "HF_HOME": model_cache_root / "hf_home",
    "TRANSFORMERS_CACHE": model_cache_root / "transformers",
    "HUGGINGFACE_HUB_CACHE": model_cache_root / "hub",
    "TORCH_HOME": model_cache_root / "torch",
    "SENTENCE_TRANSFORMERS_HOME": model_cache_root / "sentence_transformers",
}

for env_key, path in cache_paths.items():
    os.environ.setdefault(env_key, str(path))
    path.mkdir(parents=True, exist_ok=True)

from routes import router, warmup_pipelines

app = FastAPI()

cors_origins_raw = os.getenv("CORS_ALLOW_ORIGINS", "").strip()
cors_allow_all = cors_origins_raw == "*"
cors_origins = [origin.strip() for origin in cors_origins_raw.split(",") if origin.strip()] if cors_origins_raw else []

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if cors_allow_all else cors_origins,
    allow_credentials=not cors_allow_all,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.get("/health")
def health():
    return {"message": "Fact Checking System Running"}

@app.get("/")
def root():
    return {"message": "Backend is running", "health": "/health", "docs": "/docs"}

@app.on_event("startup")
async def startup_warmup():
    disable_startup_warmup = os.getenv("DISABLE_STARTUP_WARMUP", "0") == "1"
    if is_vercel or disable_startup_warmup:
        print("Startup warmup skipped: serverless mode")
        return
    try:
        await warmup_pipelines()
        print("Startup warmup complete: text/image/pdf pipelines primed")
    except Exception as exc:
        print(f"Startup warmup skipped: {exc}")
