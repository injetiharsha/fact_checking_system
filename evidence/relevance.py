# evidence/relevance.py

from sentence_transformers import SentenceTransformer, util
import torch


class RelevanceScorer:

    def __init__(self):
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

    def score(self, claim, text):

        if not text:
            return 0

        claim_emb = self.model.encode(claim, convert_to_tensor=True)
        text_emb = self.model.encode(text, convert_to_tensor=True)

        score = util.cos_sim(claim_emb, text_emb)[0][0].item()

        return round(score, 3)
