import argparse
import json
from pathlib import Path


FIX2_BASELINE = Path(
    "logs/multilingual_regression_v2_fix2_2026-03-22_151007/"
    "multilingual_regression_batch_v2_fix2_results.json"
)


def load_result(path: Path):
    payload = json.loads(path.read_text(encoding="utf-8"))
    metrics = payload.get("benchmark_metrics", {})
    run_validity = payload.get("run_validity", {})
    failures = metrics.get("failed_claims", [])
    failure_map = {
        item.get("claim", ""): {
            "expected": item.get("expected_verdict"),
            "predicted": item.get("predicted_verdict"),
            "category": item.get("failure_category"),
        }
        for item in failures
    }
    return metrics, failure_map, run_validity


def is_search_collapsed(metrics):
    total = int(metrics.get("total_claims", 0) or 0)
    neutral_rate = float(metrics.get("neutral_rate", 0.0) or 0.0)
    failures = metrics.get("failed_claims", [])
    insufficient = sum(
        1 for item in failures if item.get("failure_category") == "insufficient_evidence"
    )
    return neutral_rate >= 0.8 or (total > 0 and insufficient >= max(5, total // 2))


def print_summary(label, metrics):
    print(label)
    print(f"  accuracy: {metrics.get('accuracy')}")
    print(f"  neutral_rate: {metrics.get('neutral_rate')}")
    print(f"  false_positive_rate: {metrics.get('false_positive_rate')}")
    print(f"  false_negative_rate: {metrics.get('false_negative_rate')}")
    print(f"  correct_predictions: {metrics.get('correct_predictions')}/{metrics.get('total_claims')}")


def main():
    parser = argparse.ArgumentParser(
        description="Analyze a Phase 5 multilingual rerun against the fix2 baseline."
    )
    parser.add_argument("candidate", help="Path to the rerun JSON artifact.")
    args = parser.parse_args()

    candidate_path = Path(args.candidate)
    baseline_metrics, baseline_failures, _ = load_result(FIX2_BASELINE)
    candidate_metrics, candidate_failures, candidate_validity = load_result(candidate_path)

    print_summary("Baseline (fix2)", baseline_metrics)
    print_summary("Candidate", candidate_metrics)
    print()

    if candidate_validity:
        print(f"Candidate run_validity: {candidate_validity.get('status')}")
        print()

    if candidate_validity.get("is_valid_comparison") is False or is_search_collapsed(candidate_metrics):
        print("Decision: INVALID_RUN")
        print("Reason: run is dominated by missing evidence / search collapse.")
        return

    accuracy_delta = float(candidate_metrics.get("accuracy", 0.0) or 0.0) - float(
        baseline_metrics.get("accuracy", 0.0) or 0.0
    )
    fp_delta = float(candidate_metrics.get("false_positive_rate", 0.0) or 0.0) - float(
        baseline_metrics.get("false_positive_rate", 0.0) or 0.0
    )
    neutral_delta = float(candidate_metrics.get("neutral_rate", 0.0) or 0.0) - float(
        baseline_metrics.get("neutral_rate", 0.0) or 0.0
    )

    print("Metric deltas vs fix2")
    print(f"  accuracy_delta: {accuracy_delta:+.3f}")
    print(f"  false_positive_rate_delta: {fp_delta:+.3f}")
    print(f"  neutral_rate_delta: {neutral_delta:+.3f}")
    print()

    focus_claims = [
        "मुंबई भारत की राजधानी है।",
        "பெங்களூரு இந்தியாவின் தலைநகரம்.",
        "ಬೆಂಗಳೂರು ಭಾರತದ ರಾಜಧಾನಿ.",
        "ఇవి మీకు అందకపోతే మార్చి 31లోగా ఈ పని చేయండి ఏపీలోని రైతులకు బిగ్ అలర్ట్.",
    ]
    print("Focus claim comparison")
    for claim in focus_claims:
        base = baseline_failures.get(claim, {"predicted": "CORRECT"})
        cand = candidate_failures.get(claim, {"predicted": "CORRECT"})
        print(f"- {claim}")
        print(f"  baseline: {base.get('predicted')}")
        print(f"  candidate: {cand.get('predicted')}")
    print()

    if fp_delta <= 0 and accuracy_delta >= 0 and neutral_delta <= 0:
        print("Decision: IMPROVED_OR_EQUAL")
        print("Interpretation: candidate is at least as safe as fix2.")
    elif fp_delta > 0:
        print("Decision: REGRESSION")
        print("Interpretation: candidate increased false-positive risk versus fix2.")
    else:
        print("Decision: MIXED")
        print("Interpretation: candidate is valid but still needs manual focus-claim review.")


if __name__ == "__main__":
    main()
