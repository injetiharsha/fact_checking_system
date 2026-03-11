import torch
import torch.nn.functional as F
from sentence_transformers import SentenceTransformer, util
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from training.common.config import runtime_model_settings


class RelevanceScorer:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = None
        self.tokenizer = None
        self.model_type = None

        runtime = runtime_model_settings("relevance")
        checkpoint = runtime.get("checkpoint")
        if runtime.get("enabled") and checkpoint is not None:
            try:
                self.tokenizer = AutoTokenizer.from_pretrained(str(checkpoint))
                self.model = AutoModelForSequenceClassification.from_pretrained(
                    str(checkpoint)
                ).to(self.device)
                self.model.eval()
                self.model_type = "cross_encoder"
                print(f"RelevanceScorer using trained reranker checkpoint: {checkpoint}")
                return
            except Exception as exc:
                print(f"Relevance reranker load failed: {exc}")

        for model_name in ("BAAI/bge-small-en-v1.5", "all-MiniLM-L6-v2"):
            try:
                self.model = SentenceTransformer(model_name, local_files_only=True)
                self.model_type = "bi_encoder"
                print(f"RelevanceScorer using cached model: {model_name}")
                break
            except Exception:
                continue

        if self.model is None:
            print("RelevanceScorer fallback: lexical overlap mode")

    def score(self, claim, text):
        if not text:
            return 0

        if self.model_type == "cross_encoder" and self.model is not None and self.tokenizer is not None:
            inputs = self.tokenizer(
                claim,
                text,
                return_tensors="pt",
                truncation=True,
                padding=True,
                max_length=256,
            ).to(self.device)
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
            if logits.shape[-1] == 1:
                score = torch.sigmoid(logits[0][0]).item()
            else:
                score = F.softmax(logits, dim=-1)[0][-1].item()
            return round(float(score), 3)

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
