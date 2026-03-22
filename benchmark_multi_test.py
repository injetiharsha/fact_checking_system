import asyncio
import argparse
import json
import os
import time
from collections import Counter
from pathlib import Path

from pipeline.document_pipeline import DocumentPipeline

pipeline = DocumentPipeline()

# limit concurrent pipelines (important for scraping stability)
MAX_CONCURRENT = int(os.getenv("BENCHMARK_MAX_CONCURRENT", "4"))
semaphore = asyncio.Semaphore(MAX_CONCURRENT)


# ------------------------------------------------
# Benchmark claims
# ------------------------------------------------

claims = [

    "The moon landing was faked",
    "Climate change is a hoax",
    "Drinking bleach cures COVID-19",
    "5G networks spread coronavirus",
    "The Great Wall of China is visible from space",

    "Australia is both a country and a continent",
    "The Amazon River is the longest river in the world",
    "Africa is the largest continent on Earth",
    "Greenland is the largest island in the world",
    "Lake Baikal is the deepest lake on Earth",

    "Sound travels faster in water than in air",
    "Humans share about 50 percent of their DNA with bananas",
    "Lightning is hotter than the surface of the Sun",
    "Water expands when it freezes",
    "Venus rotates in the opposite direction to most planets",

    "Jupiter is the largest planet in the solar system",
    "Mars has two moons",
    "Neptune is the farthest planet from the Sun",
    "The Sun is a star",
    "Saturn has rings",

    "World War II ended in 1945",
    "The Roman Empire fell in 476 AD",
    "The printing press was invented by Johannes Gutenberg",
    "The Berlin Wall fell in 1989",
    "The United Nations was founded after World War II",

    "Bats are the only mammals capable of true flight",
    "Sharks are older than trees",
    "Octopuses have three hearts",
    "Bananas are berries",
    "Humans can breathe in space without equipment"
]


# ------------------------------------------------
# Ground truth
# ------------------------------------------------

ground_truth = [

    "FALSE","FALSE","FALSE","FALSE","FALSE",
    "TRUE","FALSE","FALSE","TRUE","TRUE",
    "TRUE","TRUE","TRUE","TRUE","TRUE",
    "TRUE","TRUE","TRUE","TRUE","TRUE",
    "TRUE","TRUE","TRUE","TRUE","TRUE",
    "TRUE","TRUE","TRUE","TRUE","FALSE"
]


def load_claim_batch(path: str | None):
    if not path:
        return claims, ground_truth

    batch_path = Path(path)
    payload = json.loads(batch_path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, list):
        raise ValueError("Claims file must be a JSON list of {claim, expected_verdict} items.")

    loaded_claims = []
    loaded_truth = []
    for idx, row in enumerate(payload):
        if not isinstance(row, dict):
            raise ValueError(f"Invalid item at index {idx}: expected object.")
        claim = row.get("claim")
        verdict = row.get("expected_verdict")
        if not claim or not verdict:
            raise ValueError(f"Missing claim or expected_verdict at index {idx}.")
        loaded_claims.append(str(claim))
        loaded_truth.append(str(verdict).upper())
    return loaded_claims, loaded_truth


# ------------------------------------------------
# Process a single claim
# ------------------------------------------------

async def process_claim(i, claim, active_claims, active_truth):

    async with semaphore:

        print("\n==============================")
        print(f"Processing claim {i+1}/{len(active_claims)}")
        print("Claim:", claim)

        start = time.time()

        error_text = None
        try:
            res = await pipeline._process_text(claim)
        except Exception as exc:
            res = {
                "final_verdict": "NEUTRAL",
                "logical_analysis": {},
                "evidence": [],
                "error": str(exc),
            }
            error_text = str(exc)
            print("Claim processing error:", error_text)

        elapsed = round(time.time() - start, 3)

        claim_result = None
        if isinstance(res, dict):
            out_results = res.get("results")
            if isinstance(out_results, list) and out_results and isinstance(out_results[0], dict):
                claim_result = out_results[0]
            elif "final_verdict" in res:
                claim_result = res

        if not claim_result:
            claim_result = {"final_verdict": "NEUTRAL", "logical_analysis": {}, "evidence": []}

        verdict = claim_result.get("final_verdict", "NEUTRAL")

        print("Verdict:", verdict)
        print("Time:", elapsed, "sec")

        return {
            "claim": claim,
            "predicted_verdict": verdict,
            "expected_verdict": active_truth[i],
            "time_seconds": elapsed,
            "logical_analysis": claim_result.get("logical_analysis", {}),
            "pipeline_output": res,
            "error": error_text,
        }


# ------------------------------------------------
# Run benchmark (parallel)
# ------------------------------------------------

async def run_benchmark(active_claims, active_truth):

    start = time.time()

    tasks = [
        process_claim(i, claim, active_claims, active_truth)
        for i, claim in enumerate(active_claims)
    ]

    results = await asyncio.gather(*tasks)

    total_time = round(time.time() - start, 3)

    claim_times = [r["time_seconds"] for r in results]

    print("\n==============================")
    print("Total benchmark time:", total_time, "sec")

    return results, claim_times, total_time


# ------------------------------------------------
# Evaluation metrics
# ------------------------------------------------

def evaluate(results):
    correct = 0
    neutral = 0
    tp = 0
    tn = 0
    fp = 0
    fn = 0
    predicted_positive = 0
    predicted_negative = 0
    actual_positive = 0
    actual_negative = 0
    failed_by_expected = Counter()
    failed_by_predicted = Counter()
    failed_by_tag = Counter()
    failed_claims = []
    failed_by_category = Counter()

    def infer_failure_category(pred, truth, tags, evidence_items):
        support_n = sum(1 for e in evidence_items if e.get("stance") == "SUPPORT")
        refute_n = sum(1 for e in evidence_items if e.get("stance") == "REFUTE")

        if pred == "NEUTRAL":
            if not evidence_items:
                return "insufficient_evidence"
            return "neutral_despite_evidence"

        if truth == "TRUE" and pred != "TRUE":
            if "numeric" in tags:
                return "false_negative_numeric"
            if refute_n > support_n:
                return "false_negative_refute_bias"
            return "false_negative_general"

        if truth == "FALSE" and pred != "FALSE":
            if "numeric" in tags:
                return "false_positive_numeric"
            if support_n >= refute_n and support_n > 0:
                return "false_positive_support_bias"
            return "false_positive_general"

        return "other"

    for r in results:

        pred = r["predicted_verdict"]
        truth = r["expected_verdict"]
        analysis = r.get("logical_analysis", {})
        is_pos = truth == "TRUE"
        pred_pos = pred == "TRUE"

        if pred == truth:
            correct += 1

        if pred == "NEUTRAL":
            neutral += 1

        if is_pos:
            actual_positive += 1
        else:
            actual_negative += 1

        if pred_pos:
            predicted_positive += 1
        else:
            predicted_negative += 1

        if pred_pos and is_pos:
            tp += 1
        elif pred_pos and not is_pos:
            fp += 1
        elif not pred_pos and is_pos:
            fn += 1
        else:
            tn += 1

        if pred != truth:
            failed_by_expected[truth] += 1
            failed_by_predicted[pred] += 1
            tags = []
            if analysis.get("is_opinion"):
                tags.append("opinion")
            if analysis.get("has_numeric_value"):
                tags.append("numeric")
            if analysis.get("is_comparative"):
                tags.append("comparative")
            if analysis.get("is_projection"):
                tags.append("projection")
            if analysis.get("is_future_claim"):
                tags.append("future")
            if not tags:
                tags = ["general"]
            for tag in tags:
                failed_by_tag[tag] += 1

            evidence_items = []
            output = r.get("pipeline_output", {})
            if isinstance(output, dict):
                out_results = output.get("results")
                if isinstance(out_results, list) and out_results and isinstance(out_results[0], dict):
                    evidence_items = out_results[0].get("evidence", []) or []
                elif "evidence" in output:
                    evidence_items = output.get("evidence", []) or []

            category = infer_failure_category(pred, truth, tags, evidence_items)
            failed_by_category[category] += 1
            failed_claims.append({
                "claim": r["claim"],
                "expected_verdict": truth,
                "predicted_verdict": pred,
                "logical_tags": tags,
                "failure_category": category,
                "time_seconds": r.get("time_seconds")
            })

    total = len(results)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) else 0.0
    )

    return {
        "total_claims": total,
        "correct_predictions": correct,
        "accuracy": round(correct / total, 3),
        "neutral_rate": round(neutral / total, 3),
        "actual_positive": actual_positive,
        "actual_negative": actual_negative,
        "predicted_positive": predicted_positive,
        "predicted_negative": predicted_negative,
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "false_positive_rate": round(fp / total, 3),
        "false_negative_rate": round(fn / total, 3),
        "precision_true_class": round(precision, 3),
        "recall_true_class": round(recall, 3),
        "f1_true_class": round(f1, 3),
        "failed_by_expected_verdict": dict(failed_by_expected),
        "failed_by_predicted_verdict": dict(failed_by_predicted),
        "failed_by_claim_tag": dict(failed_by_tag),
        "failed_by_category": dict(failed_by_category),
        "failed_claims": failed_claims
    }


def summarize_stage_timings(results):
    totals = Counter()
    per_claim = []

    for row in results:
        timings = {}
        output = row.get("pipeline_output", {})
        if isinstance(output, dict):
            out_results = output.get("results")
            if isinstance(out_results, list) and out_results and isinstance(out_results[0], dict):
                transparency = out_results[0].get("transparency", {})
                timings = transparency.get("stage_timings_seconds", {}) or {}

        clean_timings = {}
        for key, value in timings.items():
            try:
                numeric = round(float(value), 3)
            except (TypeError, ValueError):
                continue
            totals[key] += numeric
            clean_timings[key] = numeric

        if clean_timings:
            per_claim.append({
                "claim": row.get("claim"),
                "time_seconds": row.get("time_seconds"),
                "stage_timings_seconds": clean_timings,
            })

    rounded_totals = {key: round(value, 3) for key, value in totals.items()}

    dominant_stage = None
    dominant_value = 0.0
    for key, value in rounded_totals.items():
        if key == "total_pipeline":
            continue
        if value > dominant_value:
            dominant_stage = key
            dominant_value = value

    model_locked_total = round(
        rounded_totals.get("relevance_model_inference", 0.0)
        + rounded_totals.get("stance_model_inference", 0.0)
        + rounded_totals.get("llm_verifier", 0.0),
        3,
    )

    return {
        "stage_timing_totals_seconds": rounded_totals,
        "dominant_stage": dominant_stage,
        "dominant_stage_seconds": dominant_value,
        "model_locked_total_seconds": model_locked_total,
        "per_claim_stage_timings": per_claim,
    }


# ------------------------------------------------
# Save results
# ------------------------------------------------

def save_results(results, metrics, claim_times, total_time, output_path):
    stage_summary = summarize_stage_timings(results)

    output = {
        "benchmark_metrics": metrics,
        "total_time_seconds": total_time,
        "average_claim_time": round(sum(claim_times)/len(claim_times),3),
        "stage_timing_summary": stage_summary,
        "claims": results
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"\nResults saved to {output_path}")


# ------------------------------------------------
# Main
# ------------------------------------------------

async def main():
    parser = argparse.ArgumentParser(description="Run the multi-claim benchmark.")
    parser.add_argument("--claims-file", default=None, help="Optional JSON file with {claim, expected_verdict} rows.")
    parser.add_argument("--output", default="parallel_test_results.json", help="Output JSON path.")
    args = parser.parse_args()

    active_claims, active_truth = load_claim_batch(args.claims_file)
    results, claim_times, total_time = await run_benchmark(active_claims, active_truth)

    metrics = evaluate(results)

    print("\n==============================")
    print("BENCHMARK METRICS")
    print("==============================")

    summary_keys = [
        "total_claims", "correct_predictions", "accuracy", "neutral_rate",
        "actual_positive", "actual_negative",
        "predicted_positive", "predicted_negative",
        "tp", "tn", "fp", "fn",
        "false_positive_rate", "false_negative_rate",
        "precision_true_class", "recall_true_class", "f1_true_class"
    ]
    for key in summary_keys:
        print(key, ":", metrics.get(key))

    print("failed_by_expected_verdict :", metrics.get("failed_by_expected_verdict"))
    print("failed_by_predicted_verdict :", metrics.get("failed_by_predicted_verdict"))
    print("failed_by_claim_tag :", metrics.get("failed_by_claim_tag"))
    print("failed_by_category :", metrics.get("failed_by_category"))

    stage_summary = summarize_stage_timings(results)
    print("dominant_stage :", stage_summary.get("dominant_stage"))
    print("dominant_stage_seconds :", stage_summary.get("dominant_stage_seconds"))
    print("model_locked_total_seconds :", stage_summary.get("model_locked_total_seconds"))

    save_results(results, metrics, claim_times, total_time, args.output)


if __name__ == "__main__":
    asyncio.run(main())
