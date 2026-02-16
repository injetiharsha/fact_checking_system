import torch
from sentence_transformers import SentenceTransformer, util
import nltk


class SemanticRetriever:

    def __init__(self):
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

    def get_top_sentences(self, claim, document_text, top_k=3, threshold=0.5):

        if not document_text:
            return []

        sentences = nltk.sent_tokenize(document_text)

        if not sentences:
            return []

        claim_embedding = self.model.encode(claim, convert_to_tensor=True)
        sentence_embeddings = self.model.encode(sentences, convert_to_tensor=True)

        scores = util.cos_sim(claim_embedding, sentence_embeddings)[0]

        top_results = torch.topk(scores, k=min(top_k, len(sentences)))

        filtered_sentences = []

        for idx, score in zip(top_results.indices, top_results.values):
            if score.item() >= threshold:
                filtered_sentences.append(sentences[idx])

        return filtered_sentences
