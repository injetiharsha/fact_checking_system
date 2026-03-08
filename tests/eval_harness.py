import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _extract_claim_rows(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    if isinstance(payload.get("claims"), list):
        return payload["claims"]
    if isinstance(payload.get("results"), list):
        return payload["results"]
    return []


def _extract_claim_confidence(row: Dict[str, Any]) -> Optional[float]:
    output = row.get("pipeline_output")
    if isinstance(output, dict):
        results = output.get("results")
        if isinstance(results, list) and results and isinstance(results[0], dict):
            conf = results[0].get("confidence")
            if conf is not None:
                return _safe_float(conf, None)
    conf = row.get("confidence")
    if conf is not None:
        return _safe_float(conf, None)
    return None


def compute_eval_metrics(payload: Dict[str, Any]) -> Dict[str, Any]:
    benchmark = payload.get("benchmark_metrics", {}) if isinstance(payload, dict) else {}
    rows = _extract_claim_rows(payload if isinstance(payload, dict) else {})
    total = int(benchmark.get("total_claims") or len(rows) or 0)
    correct = int(benchmark.get("correct_predictions", 0))

    contradiction_errors = 0
    abstain_errors = 0
    confidence_values: List[float] = []

    for row in rows:
        pred = str(row.get("predicted_verdict", "")).upper()
        truth = str(row.get("expected_verdict", "")).upper()
        if pred == "NEUTRAL" and truth in {"TRUE", "FALSE"} and pred != truth:
            abstain_errors += 1
        if (pred, truth) in {("TRUE", "FALSE"), ("FALSE", "TRUE")}:
            contradiction_errors += 1
        conf = _extract_claim_confidence(row)
        if conf is not None:
            confidence_values.append(conf)

    accuracy = float(benchmark.get("accuracy", 0.0))
    neutral_rate = float(benchmark.get("neutral_rate", 0.0))
    contradiction_error_rate = (contradiction_errors / total) if total else 0.0
    abstain_error_rate = (abstain_errors / total) if total else 0.0
    avg_confidence = (sum(confidence_values) / len(confidence_values)) if confidence_values else 0.0

    return {
        "total_claims": total,
        "correct_predictions": correct,
        "accuracy": round(accuracy, 4),
        "neutral_rate": round(neutral_rate, 4),
        "contradiction_errors": contradiction_errors,
        "contradiction_error_rate": round(contradiction_error_rate, 4),
        "abstain_errors": abstain_errors,
        "abstain_error_rate": round(abstain_error_rate, 4),
        "average_confidence": round(avg_confidence, 4),
    }


def compare_metrics(current: Dict[str, Any], baseline: Dict[str, Any]) -> Dict[str, Any]:
    keys = [
        "accuracy",
        "neutral_rate",
        "contradiction_error_rate",
        "abstain_error_rate",
        "average_confidence",
    ]
    deltas: Dict[str, float] = {}
    for key in keys:
        deltas[key] = round(_safe_float(current.get(key)) - _safe_float(baseline.get(key)), 4)
    return deltas


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def print_report(title: str, metrics: Dict[str, Any]) -> None:
    print(f"\n{title}")
    print("-" * len(title))
    for key in [
        "total_claims",
        "correct_predictions",
        "accuracy",
        "neutral_rate",
        "contradiction_errors",
        "contradiction_error_rate",
        "abstain_errors",
        "abstain_error_rate",
        "average_confidence",
    ]:
        print(f"{key}: {metrics.get(key)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate benchmark output and compare to baseline.")
    parser.add_argument("--current", required=True, help="Path to current benchmark JSON")
    parser.add_argument("--baseline", required=False, help="Path to baseline benchmark JSON")
    args = parser.parse_args()

    current_payload = load_json(Path(args.current))
    current_metrics = compute_eval_metrics(current_payload)
    print_report("Current Run Metrics", current_metrics)

    if args.baseline:
        baseline_payload = load_json(Path(args.baseline))
        baseline_metrics = compute_eval_metrics(baseline_payload)
        print_report("Baseline Run Metrics", baseline_metrics)
        deltas = compare_metrics(current_metrics, baseline_metrics)
        print("\nMetric Delta (current - baseline)")
        print("----------------------------------")
        for key, value in deltas.items():
            print(f"{key}: {value:+.4f}")


if __name__ == "__main__":
    main()
