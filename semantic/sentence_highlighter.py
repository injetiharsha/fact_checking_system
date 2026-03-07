# semantic/sentence_highlighter.py

import nltk
import torch
from models.embeddings.sentence_model import EmbeddingModel


class SentenceHighlighter:

    def __init__(self):
        self.encoder = EmbeddingModel()

    def highlight(self, claim, document_text):

        if not document_text:
            return None

        sentences = nltk.sent_tokenize(document_text)

        if not sentences:
            return None

        # remove extremely short sentences
        sentences = [
            s.strip()
            for s in sentences
            if len(s.split()) > 5
        ]

        if not sentences:
            return None

        # limit sentences for speed
        sentences = sentences[:40]

        claim_emb = self.encoder.encode([claim])
        sent_embs = self.encoder.encode(sentences)

        scores = torch.nn.functional.cosine_similarity(
            claim_emb, sent_embs
        )

        best_idx = torch.argmax(scores).item()

        return sentences[best_idx]