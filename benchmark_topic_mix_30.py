from dotenv import load_dotenv
load_dotenv()

import asyncio
import argparse
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

from pipeline.claim_pipeline import ClaimPipeline

os.environ.setdefault("FACTLENS_CACHE_RETRIEVAL", "0")
os.environ.setdefault("FACTLENS_CACHE_EXTRACTION", "0")

pipeline = ClaimPipeline()

MAX_CONCURRENT = int(os.getenv("BENCHMARK_MAX_CONCURRENT", "4"))
CLAIM_DELAY_SECONDS = float(os.getenv("BENCHMARK_CLAIM_DELAY_SECONDS", "0.75"))
BENCHMARK_TIMEOUT_SECONDS = float(os.getenv("BENCHMARK_TIMEOUT_SECONDS", "900"))
semaphore = asyncio.Semaphore(MAX_CONCURRENT)

LABEL_ALIASES = {
    "TRUE": "SUPPORT",
    "SUPPORT": "SUPPORT",
    "FALSE": "REFUTE",
    "REFUTE": "REFUTE",
    "REFUSE": "REFUTE",
    "NEUTRAL": "NEUTRAL",
}

DEFAULT_CLAIMS_FILE = "benchmark_claims/topic_mix_30_v1.json"


def _safe_console_text(value):
    text = str(value)
    enc = sys.stdout.encoding or "utf-8"
    return text.encode(enc, errors="replace").decode(enc, errors="replace")


def _canonical_label(value):
    return LABEL_ALIASES.get(str(value or "").strip().upper(), "NEUTRAL")


def load_claim_batch(path: str | None):
    if not path:
        path = DEFAULT_CLAIMS_FILE

    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(payload, list):
        raise ValueError("Claims file must be a JSON list of {context_label, claim, expected_verdict} items.")

    rows = []
    for idx, row in enumerate(payload):
        if not isinstance(row, dict):
            raise ValueError(f"Invalid item at index {idx}: expected object.")
        context_label = row.get("context_label")
        claim = row.get("claim")
        verdict = row.get("expected_verdict")
        if not context_label or not claim or not verdict:
            raise ValueError(f"Missing context_label, claim or expected_verdict at index {idx}.")
        rows.append({
            "context_label": str(context_label).upper(),
            "claim": str(claim),
            "expected_verdict": _canonical_label(verdict),
            "source_hint": row.get("source_hint"),
        })
    return rows


async def process_claim(i, row, total_rows):
    async with semaphore:
        claim = row["claim"]
        topic = row["context_label"]
        expected = row["expected_verdict"]

        print("\n==============================")
        print(f"Processing claim {i+1}/{len(total_rows)}")
        print("Topic:", topic)
        print("Claim:", _safe_console_text(claim))

        start = time.time()
        error_text = None
        try:
            res = await pipeline.run(claim, force_fresh_retrieval=True)
        except Exception as exc:
            res = {
                "final_verdict": "NEUTRAL",
                "logical_analysis": {},
                "evidence": [],
                "error": str(exc),
            }
            error_text = str(exc)
            print("Claim processing error:", _safe_console_text(error_text))

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

        verdict = _canonical_label(claim_result.get("final_verdict", "NEUTRAL"))

        print("Verdict:", verdict)
        print("Time:", elapsed, "sec")

        if CLAIM_DELAY_SECONDS > 0:
            await asyncio.sleep(CLAIM_DELAY_SECONDS)

        return {
            "context_label": topic,
            "claim": claim,
            "predicted_verdict": verdict,
            "expected_verdict": expected,
            "source_hint": row.get("source_hint"),
            "time_seconds": elapsed,
            "logical_analysis": claim_result.get("logical_analysis", {}),
            "pipeline_output": res,
            "error": error_text,
        }


async def run_benchmark(rows):
    start = time.time()
    tasks = [process_claim(i, row, rows) for i, row in enumerate(rows)]
    results = await asyncio.gather(*tasks)
    total_time = round(time.time() - start, 3)
    claim_times = [r["time_seconds"] for r in results]
    print("\n==============================")
    print("Total benchmark time:", total_time, "sec")
    return results, claim_times, total_time


def evaluate(results):
    labels = ("SUPPORT", "REFUTE", "NEUTRAL")
    confusion = {truth: Counter() for truth in labels}
    failed_by_expected = Counter()
    failed_by_predicted = Counter()
    failed_by_topic = Counter()
    failed_claims = []
    topic_total = Counter()
    topic_correct = Counter()
    topic_neutral = Counter()

    correct = 0
    neutral = 0
    tp = tn = fp = fn = 0
    predicted_positive = predicted_negative = 0
    actual_positive = actual_negative = 0
    binary_total = 0

    for r in results:
        pred = _canonical_label(r["predicted_verdict"])
        truth = _canonical_label(r["expected_verdict"])
        topic = r.get("context_label", "UNKNOWN")

        topic_total[topic] += 1
        if pred == truth:
            correct += 1
            topic_correct[topic] += 1
        else:
            failed_by_expected[truth] += 1
            failed_by_predicted[pred] += 1
            failed_by_topic[topic] += 1
            failed_claims.append({
                "context_label": topic,
                "claim": r["claim"],
                "expected_verdict": truth,
                "predicted_verdict": pred,
                "source_hint": r.get("source_hint"),
                "time_seconds": r.get("time_seconds"),
                "error": r.get("error"),
            })

        if pred == "NEUTRAL":
            neutral += 1
            topic_neutral[topic] += 1

        confusion.setdefault(truth, Counter())
        confusion[truth][pred] += 1

        is_pos = truth == "SUPPORT"
        pred_pos = pred == "SUPPORT"
        if truth in {"SUPPORT", "REFUTE"}:
            binary_total += 1
            if is_pos:
                actual_positive += 1
            else:
                actual_negative += 1
            if pred == "SUPPORT":
                predicted_positive += 1
            elif pred == "REFUTE":
                predicted_negative += 1

            if pred_pos and is_pos:
                tp += 1
            elif pred == "REFUTE" and not is_pos:
                tn += 1
            elif pred_pos and not is_pos:
                fp += 1
            elif pred == "REFUTE" and is_pos:
                fn += 1

    per_topic_metrics = {}
    for topic, total in sorted(topic_total.items()):
        per_topic_metrics[topic] = {
            "total_claims": total,
            "correct_predictions": topic_correct[topic],
            "accuracy": round(topic_correct[topic] / total, 3) if total else 0.0,
            "neutral_rate": round(topic_neutral[topic] / total, 3) if total else 0.0,
            "failed_predictions": failed_by_topic[topic],
        }

    return {
        "total_claims": len(results),
        "correct_predictions": correct,
        "accuracy": round(correct / len(results), 3) if results else 0.0,
        "neutral_rate": round(neutral / len(results), 3) if results else 0.0,
        "actual_positive": actual_positive,
        "actual_negative": actual_negative,
        "predicted_positive": predicted_positive,
        "predicted_negative": predicted_negative,
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "false_positive_rate": round(fp / binary_total, 3) if binary_total else 0.0,
        "false_negative_rate": round(fn / binary_total, 3) if binary_total else 0.0,
        "failed_by_expected_verdict": dict(failed_by_expected),
        "failed_by_predicted_verdict": dict(failed_by_predicted),
        "failed_by_topic": dict(failed_by_topic),
        "confusion_matrix": {k: dict(v) for k, v in confusion.items()},
        "per_topic_metrics": per_topic_metrics,
        "failed_claims": failed_claims,
    }


def save_results(results, metrics, claim_times, total_time, output_path):
    output = {
        "benchmark_metrics": metrics,
        "total_time_seconds": total_time,
        "average_claim_time": round(sum(claim_times) / len(claim_times), 3) if claim_times else 0.0,
        "claims": results,
    }
    Path(output_path).write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nResults saved to {output_path}")


async def main():
    parser = argparse.ArgumentParser(description="Run topic-balanced 30-claim benchmark.")
    parser.add_argument("--claims-file", default=None, help="Optional JSON file with {context_label, claim, expected_verdict} rows.")
    parser.add_argument("--output", default="benchmark_topic_mix_30_results.json", help="Output JSON path.")
    args = parser.parse_args()

    rows = load_claim_batch(args.claims_file)
    try:
        results, claim_times, total_time = await asyncio.wait_for(
            run_benchmark(rows),
            timeout=BENCHMARK_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        print("\n==============================")
        print(f"BENCHMARK FAILED: Timeout after {BENCHMARK_TIMEOUT_SECONDS} seconds.")
        results, claim_times, total_time = [], [], BENCHMARK_TIMEOUT_SECONDS

    metrics = evaluate(results)

    print("\n==============================")
    print("BENCHMARK METRICS")
    print("==============================")
    for key in [
        "total_claims", "correct_predictions", "accuracy", "neutral_rate",
        "actual_positive", "actual_negative",
        "predicted_positive", "predicted_negative",
        "tp", "tn", "fp", "fn",
        "false_positive_rate", "false_negative_rate",
    ]:
        print(key, ":", metrics.get(key))
    print("failed_by_expected_verdict :", metrics.get("failed_by_expected_verdict"))
    print("failed_by_predicted_verdict :", metrics.get("failed_by_predicted_verdict"))
    print("failed_by_topic :", metrics.get("failed_by_topic"))

    save_results(results, metrics, claim_times, total_time, args.output)


if __name__ == "__main__":
    asyncio.run(main())
