from dotenv import load_dotenv
load_dotenv()

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.claim_pipeline import ClaimPipeline


def _load_rows(path: str):
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(data, list):
        raise ValueError("Claims file must be a JSON list.")
    return data


def _pick_rows(rows, limit: int):
    picked = []
    seen = set()
    for row in rows:
        claim = str((row or {}).get("claim") or "").strip()
        if not claim or claim in seen:
            continue
        seen.add(claim)
        picked.append(row)
        if len(picked) >= limit:
            break
    return picked


async def _run_audit(rows, output_path: str):
    pipeline = ClaimPipeline()
    out = ["# Claim Flow Audit", ""]
    for i, row in enumerate(rows, start=1):
        claim = str(row.get("claim") or "").strip()
        expected = str(row.get("expected_verdict") or "").strip().upper()
        topic = str(row.get("context_label") or row.get("language") or "unknown")
        result = await pipeline.run(claim, force_fresh_retrieval=True)
        claim_row = result.get("results", [result])[0] if isinstance(result, dict) and "results" in result else result
        transparency = (claim_row or {}).get("transparency", {}) or {}
        routing = transparency.get("routing", {}) or {}
        audit = transparency.get("retrieval_audit", {}) or {}
        evidence = (claim_row or {}).get("evidence", []) or []

        out.append(f"## {i}. {claim}")
        out.append(f"- topic: `{topic}`")
        out.append(f"- expected: `{expected}`")
        out.append(f"- predicted: `{claim_row.get('final_verdict', 'NEUTRAL')}`")
        out.append("")

        out.append("### Queries")
        for q in routing.get("search_queries", []) or []:
            out.append(f"- `{q}`")
        if not routing.get("search_queries"):
            out.append("- none")
        out.append("")

        out.append("### Provider Chain")
        for p in routing.get("search_provider_chain", []) or []:
            out.append(f"- `{p}`")
        if not routing.get("search_provider_chain"):
            out.append("- none")
        out.append("")

        out.append("### Scrape Audit")
        scraped = audit.get("scraped_pages", []) or []
        if scraped:
            for item in scraped[:12]:
                out.append(
                    f"- url: `{item.get('url')}` | extractor: `{item.get('extractor')}` | words: `{item.get('word_count')}` | reject: `{item.get('reject_reason')}`"
                )
        else:
            out.append("- none")
        out.append("")

        out.append("### Selected Sentences")
        selected = audit.get("evidence_selected", []) or []
        if selected:
            for item in selected[:10]:
                out.append(
                    f"- `{item.get('url')}` | rel=`{item.get('relevance')}` | sel=`{item.get('selector_score')}` | overlap=`{item.get('overlap_ratio')}`"
                )
                out.append(f"  - {item.get('sentence')}")
        else:
            out.append("- none")
        out.append("")

        out.append("### Final Evidence")
        if evidence:
            for ev in evidence[:10]:
                out.append(
                    f"- stance=`{ev.get('stance')}` conf=`{ev.get('confidence')}` src=`{ev.get('stance_source')}` url=`{ev.get('url')}`"
                )
                out.append(f"  - {ev.get('text')}")
        else:
            out.append("- none")
        out.append("")

    Path(output_path).write_text("\n".join(out), encoding="utf-8")
    print(output_path)


async def main():
    parser = argparse.ArgumentParser(description="Audit retrieval/extraction/selection flow for sample claims.")
    parser.add_argument("--claims-file", required=True)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--output", default="logs/claim_flow_audit.md")
    args = parser.parse_args()

    rows = _pick_rows(_load_rows(args.claims_file), args.limit)
    await _run_audit(rows, args.output)


if __name__ == "__main__":
    asyncio.run(main())
