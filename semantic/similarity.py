# semantic/similarity.py

import torch
import torch.nn.functional as F
from semantic.encoder import SemanticEncoder


class SimilarityEngine:

    def __init__(self):
        self.encoder = SemanticEncoder()

    def compute_similarity(self, text1, text2):
        """
        Returns cosine similarity score between two texts
        """

        embeddings = self.encoder.encode([text1, text2])

        emb1 = embeddings[0]
        emb2 = embeddings[1]

        similarity = F.cosine_similarity(
            emb1.unsqueeze(0),
            emb2.unsqueeze(0)
        )

        return round(similarity.item(), 3)

    def rank_sentences(self, claim, sentences, top_k=3):
        """
        Rank list of sentences based on similarity to claim
        """

        claim_embedding = self.encoder.encode(claim)[0]
        sentence_embeddings = self.encoder.encode(sentences)

        scores = []

        for i, sentence_emb in enumerate(sentence_embeddings):
            score = F.cosine_similarity(
                claim_embedding.unsqueeze(0),
                sentence_emb.unsqueeze(0)
            ).item()

            scores.append((sentences[i], score))

        # Sort descending
        scores.sort(key=lambda x: x[1], reverse=True)

        return [s[0] for s in scores[:top_k]]
