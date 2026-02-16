# semantic/sentence_highlighter.py

import nltk
from semantic.encoder import EmbeddingModel
import torch

nltk.download("punkt")

class SentenceHighlighter:
    def __init__(self):
        self.encoder = EmbeddingModel()

    def highlight(self, claim, document_text):
        sentences = nltk.sent_tokenize(document_text)

        claim_emb = self.encoder.encode(claim)
        sent_embs = self.encoder.encode(sentences)

        scores = torch.nn.functional.cosine_similarity(
            claim_emb, sent_embs
        )

        best_idx = torch.argmax(scores).item()
        return sentences[best_idx]
