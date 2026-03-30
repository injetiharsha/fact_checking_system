import argparse
import json
import os
from contextlib import contextmanager
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

try:
    import faiss
except Exception:  # pragma: no cover - optional at build time
    faiss = None


def _model_cached(model_name):
    candidate_roots = []
    if os.getenv('MODEL_CACHE_DIR'):
        candidate_roots.append(Path(os.getenv('MODEL_CACHE_DIR')))
    if os.getenv('TRANSFORMERS_CACHE'):
        candidate_roots.append(Path(os.getenv('TRANSFORMERS_CACHE')))
    candidate_roots.append(Path(__file__).resolve().parents[1] / '.venv' / 'model_cache')
    model_dir = model_name.replace('/', '--')
    for root in candidate_roots:
        if (root / f'models--{model_dir}').exists():
            return True
        if (root / 'transformers' / f'models--{model_dir}').exists():
            return True
        if (root / 'sentence_transformers' / f'models--{model_dir}').exists():
            return True
    return False


@contextmanager
def _offline_hf():
    previous_hf = os.getenv('HF_HUB_OFFLINE')
    previous_tf = os.getenv('TRANSFORMERS_OFFLINE')
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    try:
        yield
    finally:
        if previous_hf is None:
            os.environ.pop('HF_HUB_OFFLINE', None)
        else:
            os.environ['HF_HUB_OFFLINE'] = previous_hf
        if previous_tf is None:
            os.environ.pop('TRANSFORMERS_OFFLINE', None)
        else:
            os.environ['TRANSFORMERS_OFFLINE'] = previous_tf



def _resolve_model_path(model_name):
    candidate_roots = []
    if os.getenv('MODEL_CACHE_DIR'):
        candidate_roots.append(Path(os.getenv('MODEL_CACHE_DIR')))
    if os.getenv('TRANSFORMERS_CACHE'):
        candidate_roots.append(Path(os.getenv('TRANSFORMERS_CACHE')))
    candidate_roots.append(Path(__file__).resolve().parents[1] / '.venv' / 'model_cache')
    model_dir = model_name.replace('/', '--')
    relative_candidates = [
        Path('sentence_transformers') / f'models--{model_dir}',
        Path('transformers') / f'models--{model_dir}',
        Path(f'models--{model_dir}'),
    ]
    for root in candidate_roots:
        for relative in relative_candidates:
            model_root = root / relative
            refs_main = model_root / 'refs' / 'main'
            snapshots_dir = model_root / 'snapshots'
            if refs_main.exists():
                revision = refs_main.read_text(encoding='utf-8').strip()
                snapshot = snapshots_dir / revision
                if snapshot.exists():
                    return snapshot
            if snapshots_dir.exists():
                snapshots = sorted([path for path in snapshots_dir.iterdir() if path.is_dir()])
                if snapshots:
                    return snapshots[-1]
    return None

def _read_documents(corpus_dir: Path):
    docs = []
    for path in sorted(corpus_dir.rglob('*')):
        if path.suffix.lower() not in {'.txt', '.md'}:
            continue
        if path.name.lower() == 'readme.md':
            continue
        text = path.read_text(encoding='utf-8', errors='ignore').strip()
        if not text:
            continue
        docs.extend(_chunk_document(path, text))
    return docs


def _chunk_document(path: Path, text: str):
    chunks = []
    normalized = text.replace('\r\n', '\n')
    paragraphs = [part.strip() for part in normalized.split('\n\n') if part.strip()]
    buffer = []
    source = 'Local Corpus'
    url = ''
    title = path.stem.replace('_', ' ').strip()

    for para in paragraphs:
        lowered = para.lower()
        if lowered.startswith('source:'):
            source = para.split(':', 1)[1].strip() or source
            continue
        if lowered.startswith('url:'):
            url = para.split(':', 1)[1].strip()
            continue
        if lowered.startswith('title:'):
            title = para.split(':', 1)[1].strip() or title
            continue
        buffer.append(para)

    if not buffer:
        return []

    joined = ' '.join(buffer)
    words = joined.split()
    window = 120
    stride = 90
    for start in range(0, max(len(words), 1), stride):
        chunk_words = words[start:start + window]
        if len(chunk_words) < 20:
            if start > 0:
                break
        chunk_text = ' '.join(chunk_words).strip()
        if not chunk_text:
            continue
        chunks.append({
            'source': source,
            'url': url,
            'title': title,
            'file_name': path.name,
            'text': chunk_text,
        })
        if start + window >= len(words):
            break
    return chunks


def _load_encoder(requested_model: str):
    device = os.getenv("LOCAL_RAG_DEVICE", "cpu").strip().lower()
    last_exc = None
    for candidate in (requested_model, 'all-MiniLM-L6-v2'):
        if not _model_cached(candidate) and not _model_cached(f'sentence-transformers/{candidate}'):
            continue
        try:
            with _offline_hf():
                return SentenceTransformer(candidate, device=device)
        except Exception as exc:
            last_exc = exc
    if last_exc is not None:
        raise last_exc
    raise RuntimeError('No local embedding model available')


def build_local_rag_index(corpus_dir: str | Path, index_dir: str | Path, model_name: str):
    corpus_dir = Path(corpus_dir)
    index_dir = Path(index_dir)
    index_dir.mkdir(parents=True, exist_ok=True)

    docs = _read_documents(corpus_dir)
    if not docs:
        raise RuntimeError(f'No corpus documents found in {corpus_dir}')

    model = _load_encoder(model_name)
    embeddings = model.encode(
        [doc['text'] for doc in docs],
        batch_size=16,
        show_progress_bar=False,
        normalize_embeddings=True,
    )
    matrix = np.asarray(embeddings, dtype='float32')
    if faiss is not None:
        index = faiss.IndexFlatIP(matrix.shape[1])
        index.add(matrix)
        faiss.write_index(index, str(index_dir / 'trusted.faiss'))
    else:
        np.save(index_dir / 'trusted_embeddings.npy', matrix)

    (index_dir / 'trusted_metadata.json').write_text(
        json.dumps(docs, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )
    return len(docs)


def main():
    parser = argparse.ArgumentParser(description='Build a local trusted-corpus FAISS index.')
    parser.add_argument('--corpus-dir', default='data/trusted_corpus')
    parser.add_argument('--index-dir', default='data/trusted_corpus/index')
    parser.add_argument('--model-name', default='all-MiniLM-L6-v2')
    args = parser.parse_args()

    count = build_local_rag_index(args.corpus_dir, args.index_dir, args.model_name)
    print(f'Built local RAG index with {count} chunks')


if __name__ == '__main__':
    main()








