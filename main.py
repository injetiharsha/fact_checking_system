import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI

# Load env first and force model caches to a custom local path.
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

model_cache_root = Path(
    os.getenv("MODEL_CACHE_DIR", r"F:\fact_checking_system\.venv\model_cache")
).expanduser()

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

from routes import router

app = FastAPI()
app.include_router(router)

@app.get("/")
def root():
    return {"message": "Fact Checking System Running"}
