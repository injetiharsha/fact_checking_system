import json
import os
from pathlib import Path
from contextlib import contextmanager

import numpy as np
from sentence_transformers import SentenceTransformer

try:
    import faiss
except Exception:  # pragma: no cover - optional import at runtime
    faiss = None


def _model_cached(model_name):
    candidate_roots = []
    if os.getenv("MODEL_CACHE_DIR"):
        candidate_roots.append(Path(os.getenv("MODEL_CACHE_DIR")))
    if os.getenv("TRANSFORMERS_CACHE"):
        candidate_roots.append(Path(os.getenv("TRANSFORMERS_CACHE")))
    candidate_roots.append(Path(__file__).resolve().parents[1] / ".venv" / "model_cache")
    model_dir = model_name.replace("/", "--")
    for root in candidate_roots:
        if (root / f"models--{model_dir}").exists():
            return True
        if (root / "transformers" / f"models--{model_dir}").exists():
            return True
        if (root / "sentence_transformers" / f"models--{model_dir}").exists():
            return True
    return False


def _resolve_model_path(model_name):
    candidate_roots = []
    if os.getenv("MODEL_CACHE_DIR"):
        candidate_roots.append(Path(os.getenv("MODEL_CACHE_DIR")))
    if os.getenv("TRANSFORMERS_CACHE"):
        candidate_roots.append(Path(os.getenv("TRANSFORMERS_CACHE")))
    candidate_roots.append(Path(__file__).resolve().parents[1] / ".venv" / "model_cache")
    model_dir = model_name.replace("/", "--")
    relative_candidates = [
        Path("sentence_transformers") / f"models--{model_dir}",
        Path("transformers") / f"models--{model_dir}",
        Path(f"models--{model_dir}"),
    ]
    for root in candidate_roots:
        for relative in relative_candidates:
            model_root = root / relative
            refs_main = model_root / "refs" / "main"
            snapshots_dir = model_root / "snapshots"
            if refs_main.exists():
                revision = refs_main.read_text(encoding="utf-8").strip()
                snapshot = snapshots_dir / revision
                if snapshot.exists():
                    return snapshot
            if snapshots_dir.exists():
                snapshots = sorted([path for path in snapshots_dir.iterdir() if path.is_dir()])
                if snapshots:
                    return snapshots[-1]
    return None


class LocalRAGRetriever:

    def __init__(self):
        self.enabled = os.getenv("ENABLE_LOCAL_RAG", "0").strip().lower() in {"1", "true", "yes", "on"}
        self.corpus_dir = Path(os.getenv("LOCAL_RAG_CORPUS_DIR", "data/trusted_corpus"))
        self.index_dir = Path(os.getenv("LOCAL_RAG_INDEX_DIR", str(self.corpus_dir / "index")))
        self.top_k = int(os.getenv("LOCAL_RAG_TOP_K", "3"))
        self.embedding_model = os.getenv("LOCAL_RAG_EMBED_MODEL", "all-MiniLM-L6-v2")
        self.device = os.getenv("LOCAL_RAG_DEVICE", "cpu").strip().lower()
        self.auto_build = os.getenv("LOCAL_RAG_AUTO_BUILD", "0").strip().lower() in {"1", "true", "yes", "on"}
        self._encoder = None
        self._index = None
        self._metadata = []
        self._embeddings = None
        self._error = None

    def fetch(self, claim):
        if not self.enabled:
            return []

        self._ensure_loaded()
        if self._error is not None or self._index is None or not self._metadata:
            return []

        try:
            query_embedding = self._get_encoder().encode([claim], normalize_embeddings=True)
            query_vector = np.asarray(query_embedding, dtype="float32")
            if self._index is not None:
                _, indices = self._index.search(query_vector, self.top_k)
                chosen = indices[0]
            else:
                scores = np.dot(self._embeddings, query_vector[0])
                chosen = np.argsort(scores)[::-1][: self.top_k]

            evidence = []
            for idx in chosen:
                if idx < 0 or idx >= len(self._metadata):
                    continue
                row = self._metadata[idx]
                evidence.append({
                    "source": row.get("source", row.get("title", "Local Corpus")),
                    "url": row.get("url", ""),
                    "text": row.get("text", "")[:1200],
                    "weight": 0.9,
                })
            return evidence
        except Exception as e:
            print("Local RAG query error:", e)
            return []

    def _ensure_loaded(self):
        if (self._index is not None or self._embeddings is not None) or self._error is not None:
            return

        index_path = self.index_dir / "trusted.faiss"
        embedding_path = self.index_dir / "trusted_embeddings.npy"
        metadata_path = self.index_dir / "trusted_metadata.json"

        if (not index_path.exists() and not embedding_path.exists()) or not metadata_path.exists():
            if self.auto_build:
                try:
                    from scripts.build_local_rag_index import build_local_rag_index
                    build_local_rag_index(
                        corpus_dir=self.corpus_dir,
                        index_dir=self.index_dir,
                        model_name=self.embedding_model,
                    )
                except Exception as e:
                    self._error = e
                    print("Local RAG auto-build failed:", e)
                    return
            else:
                self._error = FileNotFoundError(f"Missing local RAG index files under {self.index_dir}")
                return

        try:
            self._metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            if index_path.exists() and faiss is not None:
                self._index = faiss.read_index(str(index_path))
            elif embedding_path.exists():
                self._embeddings = np.load(embedding_path)
            else:
                raise FileNotFoundError("No local RAG vector data found.")
        except Exception as e:
            self._error = e
            print("Local RAG load error:", e)

    def _get_encoder(self):
        if self._encoder is None:
            last_exc = None
            for model_name in (self.embedding_model, "all-MiniLM-L6-v2"):
                if not _model_cached(model_name) and not _model_cached(f"sentence-transformers/{model_name}"):
                    continue
                try:
                    local_path = _resolve_model_path(model_name) or _resolve_model_path(f"sentence-transformers/{model_name}")
                    model_ref = str(local_path) if local_path is not None else model_name
                    with _offline_hf():
                        self._encoder = SentenceTransformer(model_ref, device=self.device)
                    print(f"LocalRAGRetriever using cached model: {model_name} on {self.device}")
                    break
                except Exception as exc:
                    last_exc = exc
            if self._encoder is None and last_exc is not None:
                raise last_exc
        return self._encoder


@contextmanager
def _offline_hf():
    previous_hf = os.getenv("HF_HUB_OFFLINE")
    previous_tf = os.getenv("TRANSFORMERS_OFFLINE")
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    try:
        yield
    finally:
        if previous_hf is None:
            os.environ.pop("HF_HUB_OFFLINE", None)
        else:
            os.environ["HF_HUB_OFFLINE"] = previous_hf
        if previous_tf is None:
            os.environ.pop("TRANSFORMERS_OFFLINE", None)
        else:
            os.environ["TRANSFORMERS_OFFLINE"] = previous_tf

