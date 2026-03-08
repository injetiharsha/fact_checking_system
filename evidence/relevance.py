from sentence_transformers import SentenceTransformer, util


class RelevanceScorer:

    def __init__(self):
        self.model = None
        for model_name in ("BAAI/bge-small-en-v1.5", "all-MiniLM-L6-v2"):
            try:
                self.model = SentenceTransformer(model_name, local_files_only=True)
                print(f"RelevanceScorer using cached model: {model_name}")
                break
            except Exception:
                continue

        if self.model is None:
            print("RelevanceScorer fallback: lexical overlap mode")

    def score(self, claim, text):
        if not text:
            return 0

        if self.model is None:
            claim_words = set((claim or "").lower().split())
            text_words = set((text or "").lower().split())
            if not claim_words:
                return 0
            return round(len(claim_words & text_words) / len(claim_words), 3)

        claim_emb = self.model.encode(claim, convert_to_tensor=True)
        text_emb = self.model.encode(text, convert_to_tensor=True)
        score = util.cos_sim(claim_emb, text_emb)[0][0].item()
        return round(score, 3)
