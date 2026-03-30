import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from training.common.utils import ensure_dir, read_json


def build_review_queue(benchmark_path: Path) -> List[Dict]:
    benchmark = read_json(benchmark_path)
    metrics = benchmark.get("benchmark_metrics", {}) or {}
    failed_claims = {
        item.get("claim"): item
        for item in metrics.get("failed_claims", [])
    }
    review_rows = []
    for row in benchmark.get("claims", []):
        claim = row.get("claim")
        failure = failed_claims.get(claim)
        output = row.get("pipeline_output", {}) or {}
        result_rows = output.get("results", []) if isinstance(output, dict) else []
        evidence = result_rows[0].get("evidence", []) if result_rows else []
        reasons = []
        if failure:
            reasons.append(failure.get("failure_category", "failed_claim"))
        for ev in evidence:
            if float(ev.get("confidence", 0.0)) < 0.6:
                reasons.append("low_confidence_evidence")
                break
        if not reasons:
            continue
        review_rows.append({
            "claim": claim,
            "predicted_verdict": row.get("predicted_verdict"),
            "expected_verdict": row.get("expected_verdict"),
            "reasons": sorted(set(reasons)),
            "evidence_count": len(evidence),
        })
    return review_rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Export manual review queue from benchmark artifact.")
    parser.add_argument("--benchmark", default="parallel_test_results.json")
    parser.add_argument("--output-dir", default="training_artifacts/review")
    args = parser.parse_args()

    rows = build_review_queue(Path(args.benchmark))
    output_dir = ensure_dir(args.output_dir)
    output_path = output_dir / "review_queue.json"
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(rows, handle, indent=2, ensure_ascii=False)
    print(f"Wrote {len(rows)} review items to {output_path}")


if __name__ == "__main__":
    main()
