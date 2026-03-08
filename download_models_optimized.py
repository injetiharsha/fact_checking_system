#!/usr/bin/env python3
"""Download required NLP models into project-local cache (.venv/model_cache)."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

def _configure_cache() -> Path:
    project_root = Path(__file__).resolve().parent
    cache_root = Path(
        os.getenv("MODEL_CACHE_DIR", str(project_root / ".venv" / "model_cache"))
    )

    # Disable Windows symlink/permission errors
    os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

    paths = {
        "HF_HOME": cache_root / "hf_home",
        "TRANSFORMERS_CACHE": cache_root / "transformers",
        "HUGGINGFACE_HUB_CACHE": cache_root / "hub",
        "TORCH_HOME": cache_root / "torch",
        "SENTENCE_TRANSFORMERS_HOME": cache_root / "sentence_transformers",
    }

    for key, path in paths.items():
        path.mkdir(parents=True, exist_ok=True)
        os.environ[key] = str(path)

    return cache_root

def download_sentence_transformer() -> bool:
    print("\n1) Downloading sentence-transformers model...")
    try:
        from sentence_transformers import SentenceTransformer
        SentenceTransformer("BAAI/bge-small-en-v1.5")
        SentenceTransformer("all-MiniLM-L6-v2")
        print("OK: embeddings downloaded")
        return True
    except Exception as e:
        print(f"FAIL: embeddings download failed: {e}")
        return False

def download_claim_type_model() -> bool:
    print("\n2) Downloading claim type classifier model...")
    try:
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        model_name = "distilbert-base-uncased-finetuned-sst-2-english"
        AutoTokenizer.from_pretrained(model_name)
        AutoModelForSequenceClassification.from_pretrained(model_name)
        print(f"OK: {model_name}")
        return True
    except Exception as e:
        print(f"FAIL: claim type model download failed: {e}")
        return False

def download_nli_model() -> bool:
    print("\n3) Downloading NLI model...")
    # Wipe corrupted attempts
    cache_path = Path(os.environ["TRANSFORMERS_CACHE"]) / "models--cross-encoder--nli-deberta-v3-small"
    if cache_path.exists():
        shutil.rmtree(cache_path)

    try:
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        model_name = "cross-encoder/nli-deberta-v3-small"
        
        # use_fast=False is required for DeBERTa on Windows
        AutoTokenizer.from_pretrained(model_name, use_fast=False)
        AutoModelForSequenceClassification.from_pretrained(model_name)
        print(f"OK: {model_name}")
        return True
    except Exception as e:
        print(f"FAIL: NLI model download failed: {e}")
        return False

def download_spacy_model() -> bool:
    print("\n4) Downloading spaCy model en_core_web_sm...")
    try:
        import spacy
        try:
            spacy.load("en_core_web_sm")
            print("OK: en_core_web_sm already available")
            return True
        except OSError:
            subprocess.run([sys.executable, "-m", "spacy", "download", "en_core_web_sm"], check=True)
            return True
    except Exception as e:
        print(f"FAIL: spaCy model download failed: {e}")
        return False

def download_nltk_data() -> bool:
    print("\n5) Downloading NLTK punkt...")
    try:
        import nltk
        nltk.download("punkt", quiet=True)
        print("OK: punkt downloaded")
        return True
    except Exception as e:
        print(f"FAIL: NLTK download failed: {e}")
        return False

def main() -> int:
    # Pre-check for sentencepiece before doing anything else
    try:
        import sentencepiece
    except ImportError:
        print("Required library 'sentencepiece' is installed but not active. PLEASE RESTART YOUR TERMINAL.")
        return 1

    _configure_cache()

    results = [
        ("Embeddings", download_sentence_transformer()),
        ("Claim Type Model", download_claim_type_model()),
        ("NLI Model", download_nli_model()),
        ("spaCy Model", download_spacy_model()),
        ("NLTK punkt", download_nltk_data()),
    ]

    print("\nDownload summary")
    ok = True
    for name, status in results:
        print(f"- {name}: {'OK' if status else 'FAIL'}")
        ok = ok and status

    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())