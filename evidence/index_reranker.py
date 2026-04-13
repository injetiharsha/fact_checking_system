import os
import re
from pathlib import Path

try:
    import lancedb
except Exception:  # pragma: no cover
    lancedb = None

try:
    from sentence_transformers import SentenceTransformer
except Exception:  # pragma: no cover
    SentenceTransformer = None


def _normalize_token(token):
    token = (token or "").lower().strip(".,;:!?()[]{}\"'")
    if token.endswith("ies") and len(token) > 4:
        return token[:-3] + "y"
    if token.endswith("es") and len(token) > 4:
        return token[:-2]
    if token.endswith("s") and len(token) > 3:
        return token[:-1]
    return token


def _token_set(text):
    return {
        _normalize_token(token)
        for token in re.findall(r"[A-Za-z0-9']+", text or "")
        if _normalize_token(token)
    }


def _dot(a, b):
    return sum(float(x) * float(y) for x, y in zip(a, b))


def _norm(a):
    return max(_dot(a, a) ** 0.5, 1e-8)


def _cosine(a, b):
    return _dot(a, b) / (_norm(a) * _norm(b))


class IndexReranker:
    def __init__(self):
        self.enabled = os.getenv("ENABLE_INDEX_RERANK_EXPERIMENT", "0").strip().lower() in {"1", "true", "yes", "on"}
        self.use_stance_index = os.getenv("INDEX_RERANK_USE_STANCE_INDEX", "1").strip().lower() in {"1", "true", "yes", "on"}
        self.top_k = max(4, min(20, int(os.getenv("INDEX_RERANK_TOP_K", "10"))))
        self.min_score = float(os.getenv("INDEX_RERANK_STANCE_MIN_SCORE", "10"))
        self.max_exemplars_per_label = max(1, min(6, int(os.getenv("INDEX_RERANK_MAX_EXEMPLARS_PER_LABEL", "3"))))
        self.semantic_weight = float(os.getenv("INDEX_RERANK_SEMANTIC_WEIGHT", "0.10"))
        self.exemplar_weight = float(os.getenv("INDEX_RERANK_EXEMPLAR_WEIGHT", "0.08"))
        self.entity_weight = float(os.getenv("INDEX_RERANK_ENTITY_WEIGHT", "0.05"))
        self.numeric_weight = float(os.getenv("INDEX_RERANK_NUMERIC_WEIGHT", "0.04"))
        self._db = None
        self._table = None
        self._model = None
        self._claim_cache = {}

        default_model_path = Path.home() / ".cache" / "huggingface" / "hub" / "models--krutrim-ai-labs--Vyakyarth" / "snapshots" / "34147fdaea33e3a2b85f87af2b97f11ec5b6a88b"
        self.model_path = Path(os.getenv("INDEX_RERANK_MODEL_PATH", str(default_model_path)))
        self.stance_index_dir = Path(os.getenv("INDEX_RERANK_STANCE_INDEX_DIR", "index_search/stance_index/fever_stance_index"))

    @property
    def available(self):
        return self.enabled and self._ensure_ready()

    def _ensure_ready(self):
        if not self.enabled:
            return False
        if lancedb is None or SentenceTransformer is None:
            return False
        if not self.use_stance_index:
            return False
        if self._table is None:
            index_dir = self.stance_index_dir
            if not index_dir.is_absolute():
                index_dir = Path(__file__).resolve().parents[1] / index_dir
            if not index_dir.exists():
                return False
            try:
                self._db = lancedb.connect(str(index_dir))
                self._table = self._db.open_table("evidence_pool")
            except Exception:
                self._table = None
                return False
        if self._model is None:
            if not self.model_path.exists():
                return False
            try:
                self._model = SentenceTransformer(str(self.model_path), device="cpu")
            except Exception:
                self._model = None
                return False
        return self._table is not None and self._model is not None

    def _get_claim_profile(self, claim):
        cache_key = " ".join((claim or "").strip().lower().split())
        cached = self._claim_cache.get(cache_key)
        if cached is not None:
            return cached

        hits_df = self._table.search(claim, query_type="fts").limit(self.top_k).to_pandas()
        hits = hits_df.to_dict(orient="records")
        usable = []
        for row in hits:
            label = str(row.get("label") or "").upper()
            score = float(row.get("_score") or 0.0)
            if label not in {"SUPPORTS", "REFUTES"} or score < self.min_score:
                continue
            usable.append(dict(row))

        profile = {"supports": [], "refutes": []}
        if not usable:
            self._claim_cache[cache_key] = profile
            return profile

        texts = [claim] + [str(row.get("premise") or "") for row in usable]
        embeddings = self._model.encode(texts, convert_to_tensor=False)
        claim_emb = embeddings[0]
        premise_embs = embeddings[1:]

        scored = []
        max_fts = max(float(row.get("_score") or 0.0) for row in usable) or 1.0
        for row, emb in zip(usable, premise_embs):
            semantic = _cosine(claim_emb, emb)
            combined = (0.35 * (float(row.get("_score") or 0.0) / max_fts)) + (0.65 * semantic)
            enriched = dict(row)
            enriched["semantic_score"] = float(semantic)
            enriched["combined_score"] = float(combined)
            scored.append(enriched)

        scored.sort(key=lambda row: (row["combined_score"], row["semantic_score"], float(row.get("_score") or 0.0)), reverse=True)
        for row in scored:
            bucket = "supports" if str(row.get("label")).upper() == "SUPPORTS" else "refutes"
            if len(profile[bucket]) < self.max_exemplars_per_label:
                profile[bucket].append(row)

        self._claim_cache[cache_key] = profile
        return profile

    def rerank_results(self, claim, results, trace=None):
        if not self.available or not results:
            return results

        profile = self._get_claim_profile(claim)
        if not profile["supports"] and not profile["refutes"]:
            return results

        evidence_texts = [str(item.get("text") or "")[:1200] for item in results]
        embeddings = self._model.encode([claim] + evidence_texts, convert_to_tensor=False)
        claim_emb = embeddings[0]
        evidence_embs = embeddings[1:]

        support_embs = [
            self._model.encode([str(row.get("premise") or "")], convert_to_tensor=False)[0]
            for row in profile["supports"]
        ]
        refute_embs = [
            self._model.encode([str(row.get("premise") or "")], convert_to_tensor=False)[0]
            for row in profile["refutes"]
        ]
        claim_tokens = _token_set(claim)
        claim_numbers = set(re.findall(r"\b\d+\b", claim or ""))

        reranked = []
        trace_rows = []
        for item, evidence_emb in zip(results, evidence_embs):
            row = dict(item)
            text = str(row.get("text") or "")
            row_tokens = _token_set(text)
            row_numbers = set(re.findall(r"\b\d+\b", text))
            semantic_score = _cosine(claim_emb, evidence_emb)
            support_alignment = max((_cosine(evidence_emb, emb) for emb in support_embs), default=0.0)
            refute_alignment = max((_cosine(evidence_emb, emb) for emb in refute_embs), default=0.0)
            entity_overlap = len(claim_tokens & row_tokens) / max(len(claim_tokens), 1)
            numeric_match = 1.0 if claim_numbers and row_numbers and (claim_numbers & row_numbers) else 0.0
            stance = str(row.get("stance") or "").upper()

            exemplar_bonus = 0.0
            if stance == "SUPPORT":
                exemplar_bonus = max(0.0, support_alignment - refute_alignment)
            elif stance == "REFUTE":
                exemplar_bonus = max(0.0, refute_alignment - support_alignment)

            rerank_bonus = (
                (self.semantic_weight * semantic_score)
                + (self.exemplar_weight * exemplar_bonus)
                + (self.entity_weight * entity_overlap)
                + (self.numeric_weight * numeric_match)
            )
            base_combined = float(row.get("combined_score") or 0.0)
            row["index_rerank_bonus"] = round(rerank_bonus, 4)
            row["index_rerank_semantic"] = round(semantic_score, 4)
            row["index_rerank_exemplar_bonus"] = round(exemplar_bonus, 4)
            row["index_rerank_entity_overlap"] = round(entity_overlap, 4)
            row["index_rerank_numeric_match"] = int(numeric_match)
            row["combined_score"] = round(base_combined + rerank_bonus, 4)
            reranked.append(row)

            trace_rows.append({
                "source": row.get("source"),
                "url": row.get("url"),
                "stance": row.get("stance"),
                "base_combined_score": round(base_combined, 4),
                "rerank_bonus": row["index_rerank_bonus"],
                "semantic_score": row["index_rerank_semantic"],
                "exemplar_bonus": row["index_rerank_exemplar_bonus"],
                "entity_overlap": row["index_rerank_entity_overlap"],
                "numeric_match": row["index_rerank_numeric_match"],
                "final_combined_score": row["combined_score"],
                "text": row.get("text"),
            })

        reranked.sort(
            key=lambda item: (
                float(item.get("combined_score") or 0.0),
                float(item.get("confidence") or 0.0),
                float(item.get("weight") or 0.0),
            ),
            reverse=True,
        )

        if isinstance(trace, dict):
            trace["index_rerank"] = {
                "enabled": True,
                "support_exemplars": [
                    {
                        "premise": row.get("premise"),
                        "score": round(float(row.get("combined_score") or 0.0), 4),
                    }
                    for row in profile["supports"]
                ],
                "refute_exemplars": [
                    {
                        "premise": row.get("premise"),
                        "score": round(float(row.get("combined_score") or 0.0), 4),
                    }
                    for row in profile["refutes"]
                ],
                "rows": trace_rows,
            }

        return reranked
