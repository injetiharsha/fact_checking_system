# semantic/encoder.py

from models.embeddings.sentence_model import EmbeddingModel


class SemanticEncoder:

    def __init__(self):
        self.embedding_model = EmbeddingModel()

    def encode(self, texts):
        return self.embedding_model.encode(texts)
