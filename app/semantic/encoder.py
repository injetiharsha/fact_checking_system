from sentence_transformers import SentenceTransformer
from app.semantic.cache import encode_with_cache
import torch

_device = "cuda" if torch.cuda.is_available() else "cpu"
_model = SentenceTransformer("all-MiniLM-L6-v2", device=_device)

def encode(text: str):
    if not text.strip():
        return None
    return encode_with_cache(text, _model.encode)
