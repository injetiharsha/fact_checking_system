from sentence_transformers import SentenceTransformer
from app.semantic.cache import encode_with_cache

_model = SentenceTransformer("all-MiniLM-L6-v2", device="cuda")

def encode(text: str):
    if not text.strip():
        return None
    return encode_with_cache(text, _model.encode)
