import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

print('STEP import DocumentPipeline', flush=True)
from pipeline.document_pipeline import DocumentPipeline
print('STEP construct DocumentPipeline', flush=True)
dp = DocumentPipeline()
print('STEP constructed DocumentPipeline', flush=True)
print('STEP call _process_text', flush=True)
res = asyncio.run(dp._process_text('Mars has two moons'))
print('STEP got result', flush=True)
print(type(res).__name__, flush=True)
if isinstance(res, dict):
    print(res.get('results', [{}])[0].get('final_verdict'), flush=True)
