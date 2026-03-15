import importlib
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MODULES = [
    'nltk',
    'spacy',
    'torch',
    'transformers',
    'sentence_transformers',
    'faiss',
    'evidence.general_search',
    'evidence.scraper',
    'evidence.router',
    'evidence.bge_reranker',
    'evidence.relevance',
    'models.stance.nli_model',
    'semantic.stance_model',
    'pipeline.claim_pipeline',
    'pipeline.document_pipeline',
]

print('START', flush=True)
for name in MODULES:
    print(f'IMPORT {name}', flush=True)
    importlib.import_module(name)
    print(f'OK {name}', flush=True)
print('DONE', flush=True)
