import hashlib
from functools import lru_cache

def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

@lru_cache(maxsize=5000)
def _cached_embedding(hash_key: str, text: str, encoder_id: str):
    """
    Stores embeddings keyed by:
    - text hash
    - encoder identity (future-safe)
    """
    from app.semantic.encoder import _model
    return _model.encode(text)

def encode_with_cache(text: str, encoder_fn=None):
    """
    Public cache interface.
    encoder_fn is ignored intentionally to prevent lambda caching.
    """
    key = _hash(text)
    encoder_id = "all-MiniLM-L6-v2"
    return _cached_embedding(key, text, encoder_id)
