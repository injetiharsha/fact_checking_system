# models/embeddings/sentence_model.py

from sentence_transformers import SentenceTransformer
import torch


class EmbeddingModel:

    def __init__(self):
        self.model = SentenceTransformer(
            "all-MiniLM-L6-v2",
            device="cuda" if torch.cuda.is_available() else "cpu"
        )

    def encode(self, texts, convert_to_tensor=True):
        return self.model.encode(texts, convert_to_tensor=convert_to_tensor)
