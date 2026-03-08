"""
MODEL ARCHITECTURE (CURRENT RUNTIME)

This file documents the practical runtime architecture in this repository.
"""

MODEL_ARCHITECTURE = {
    "claim_type": {
        "primary": "distilbert-base-uncased-finetuned-sst-2-english (cached)",
        "fallback": "heuristic classifier",
        "status": "fallback active unless local cache is present",
    },
    "relevance": {
        "primary": "BAAI/bge-small-en-v1.5 (cached)",
        "secondary": "all-MiniLM-L6-v2 (cached)",
        "fallback": "lexical overlap scorer",
    },
    "nli_stance": {
        "primary": "cross-encoder/nli-deberta-v3-small (cached)",
        "secondary": "ynie/roberta-large-snli_mnli_fever_anli_R1_R2_R3-nli (cached)",
        "fallback": "heuristic support/neutral",
    },
    "spacy": {
        "model": "en_core_web_sm",
        "status": "available",
    },
    "cache": {
        "root": r"F:\fact_checking_system\.venv\model_cache",
        "required": [
            "HF_HOME",
            "TRANSFORMERS_CACHE",
            "HUGGINGFACE_HUB_CACHE",
            "TORCH_HOME",
            "SENTENCE_TRANSFORMERS_HOME",
        ],
    },
}
