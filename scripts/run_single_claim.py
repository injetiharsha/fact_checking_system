import asyncio
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pipeline.document_pipeline import DocumentPipeline


async def _main():
    if len(sys.argv) < 2:
        raise SystemExit("Usage: run_single_claim.py <claim>")

    claim = " ".join(sys.argv[1:]).strip()
    pipeline = DocumentPipeline()
    response = await pipeline._process_text(claim)

    result_row = {}
    if isinstance(response, dict):
        rows = response.get("results")
        if isinstance(rows, list) and rows and isinstance(rows[0], dict):
            result_row = rows[0]
        elif "final_verdict" in response:
            result_row = response

    payload = {
        "claim": claim,
        "pipeline_output": response,
        "result_row": result_row or {},
    }
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(_main())
