import asyncio
import json
import time
from collections import Counter

from pipeline.document_pipeline import DocumentPipeline

pipeline = DocumentPipeline()

# limit concurrent pipelines (important for scraping stability)
MAX_CONCURRENT = 6
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


# ------------------------------------------------
# Process a single claim
# ------------------------------------------------

async def process_claim(i, claim):

    async with semaphore:

        print("\n==============================")
        print(f"Processing claim {i+1}/{len(claims)}")
        print("Claim:", claim)

        start = time.time()

        res = await pipeline._process_text(claim)

        elapsed = round(time.time() - start, 3)

        verdict = res["results"][0]["final_verdict"]

        print("Verdict:", verdict)
        print("Time:", elapsed, "sec")

        return {
            "claim": claim,
            "predicted_verdict": verdict,
            "expected_verdict": ground_truth[i],
            "time_seconds": elapsed,
            "logical_analysis": res["results"][0].get("logical_analysis", {}),
            "pipeline_output": res
        }


# ------------------------------------------------
# Run benchmark (parallel)
# ------------------------------------------------

async def run_benchmark():

    start = time.time()

    tasks = [
        process_claim(i, claim)
        for i, claim in enumerate(claims)
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


# ------------------------------------------------
# Save results
# ------------------------------------------------

def save_results(results, metrics, claim_times, total_time):

    output = {
        "benchmark_metrics": metrics,
        "total_time_seconds": total_time,
        "average_claim_time": round(sum(claim_times)/len(claim_times),3),
        "claims": results
    }

    with open("parallel_test_results.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print("\nResults saved to parallel_test_results.json")


# ------------------------------------------------
# Main
# ------------------------------------------------

async def main():

    results, claim_times, total_time = await run_benchmark()

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

    save_results(results, metrics, claim_times, total_time)


if __name__ == "__main__":
    asyncio.run(main())
