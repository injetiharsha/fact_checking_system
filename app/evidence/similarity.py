from sentence_transformers import SentenceTransformer, util

model = SentenceTransformer("all-MiniLM-L6-v2")

def similarity_score(claim: str, evidence_text: str) -> float:
    """
    Returns similarity score between claim and evidence.
    """
    embeddings = model.encode([claim, evidence_text], convert_to_tensor=True)
    score = util.cos_sim(embeddings[0], embeddings[1])
    return round(score.item(), 4)
