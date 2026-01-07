from app.semantic.decompose import decompose_claim
from app.verdict.aggregate import aggregate_results
from app.verdict.confidence import calibrate_confidence
from app.verdict.consensus import consensus_verdict
from app.verdict.explanation import build_explanation

from app.evidence.fetcher import _single_claim_pipeline


async def multi_claim_pipeline(claim: str):
    subclaims = decompose_claim(claim)

    results = []

    for subclaim in subclaims:
        result = await _single_claim_pipeline(subclaim)
        results.append(result)

    final = aggregate_results(results)

    return {
        "claim": claim,
        "subclaims": results,
        **final
    }
