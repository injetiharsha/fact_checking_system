from dotenv import load_dotenv
load_dotenv()
import asyncio
import argparse
import json
import os
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

from pipeline.claim_pipeline import ClaimPipeline

os.environ.setdefault("FACTLENS_CACHE_RETRIEVAL", "0")
os.environ.setdefault("FACTLENS_CACHE_EXTRACTION", "0")

pipeline = ClaimPipeline()

MAX_CONCURRENT = int(os.getenv("BENCHMARK_MAX_CONCURRENT", "4"))
CLAIM_DELAY_SECONDS = float(os.getenv("BENCHMARK_CLAIM_DELAY_SECONDS", "0.75"))
BENCHMARK_TIMEOUT_SECONDS = float(os.getenv("BENCHMARK_TIMEOUT_SECONDS", "900"))
semaphore = asyncio.Semaphore(MAX_CONCURRENT)


def _safe_console_text(value):
    text = str(value)
    enc = sys.stdout.encoding or "utf-8"
    return text.encode(enc, errors="replace").decode(enc, errors="replace")


DEFAULT_CLAIMS_FILE = "benchmark_claims/indian_languages_factual.json"


def load_claim_batch(path: str | None):
    if not path:
        path = DEFAULT_CLAIMS_FILE

    batch_path = Path(path)
    payload = json.loads(batch_path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, list):
        raise ValueError("Claims file must be a JSON list of {language, claim, expected_verdict} items.")

    loaded_rows = []
    for idx, row in enumerate(payload):
        if not isinstance(row, dict):
            raise ValueError(f"Invalid item at index {idx}: expected object.")
        claim = row.get("claim")
        verdict = row.get("expected_verdict")
        language = row.get("language")
        if not claim or not verdict or not language:
            raise ValueError(f"Missing language, claim or expected_verdict at index {idx}.")
        loaded_rows.append({
            "language": str(language).lower(),
            "claim": str(claim),
            "expected_verdict": str(verdict).upper(),
            "source_hint": row.get("source_hint"),
        })
    return loaded_rows


async def process_claim(i, row, total_rows):
    async with semaphore:
        claim = row["claim"]
        language = row["language"]
        expected = row["expected_verdict"]

        print("\n==============================")
        print(f"Processing claim {i+1}/{len(total_rows)}")
        print("Language:", language)
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

        verdict = claim_result.get("final_verdict", "NEUTRAL")

        print("Verdict:", verdict)
        print("Time:", elapsed, "sec")

        if CLAIM_DELAY_SECONDS > 0:
            await asyncio.sleep(CLAIM_DELAY_SECONDS)

        return {
            "language": language,
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
    labels = ("TRUE", "FALSE", "NEUTRAL")
    confusion = {truth: Counter() for truth in labels}
    failed_by_expected = Counter()
    failed_by_predicted = Counter()
    failed_by_language = Counter()
    failed_claims = []
    language_total = Counter()
    language_correct = Counter()
    language_neutral = Counter()

    correct = 0
    neutral = 0
    blocked_not_checkable = 0
    tp = tn = fp = fn = 0
    predicted_positive = predicted_negative = 0
    actual_positive = actual_negative = 0
    binary_total = 0

    for r in results:
        pred = r["predicted_verdict"]
        truth = r["expected_verdict"]
        language = r.get("language", "unknown")
        transparency = {}
        output = r.get("pipeline_output")
        if isinstance(output, dict):
            first = None
            rows = output.get("results")
            if isinstance(rows, list) and rows and isinstance(rows[0], dict):
                first = rows[0]
            elif "final_verdict" in output:
                first = output
            if isinstance(first, dict):
                transparency = first.get("transparency", {}) or {}

        language_total[language] += 1
        if pred == truth:
            correct += 1
            language_correct[language] += 1
        else:
            failed_by_expected[truth] += 1
            failed_by_predicted[pred] += 1
            failed_by_language[language] += 1
            failed_claims.append({
                "language": language,
                "claim": r["claim"],
                "expected_verdict": truth,
                "predicted_verdict": pred,
                "source_hint": r.get("source_hint"),
                "time_seconds": r.get("time_seconds"),
                "transparency": transparency,
                "error": r.get("error"),
            })

        if pred == "NEUTRAL":
            neutral += 1
            language_neutral[language] += 1

        confusion.setdefault(truth, Counter())
        confusion[truth][pred] += 1

        is_pos = truth == "TRUE"
        pred_pos = pred == "TRUE"
        if truth in {"TRUE", "FALSE"}:
            binary_total += 1
            if is_pos:
                actual_positive += 1
            else:
                actual_negative += 1
            if pred == "TRUE":
                predicted_positive += 1
            elif pred == "FALSE":
                predicted_negative += 1

            if pred_pos and is_pos:
                tp += 1
            elif pred == "FALSE" and not is_pos:
                tn += 1
            elif pred_pos and not is_pos:
                fp += 1
            elif pred == "FALSE" and is_pos:
                fn += 1

        checkability = ((transparency.get("claim_checkability") or {}) if isinstance(transparency, dict) else {})
        if checkability.get("allowed") is False:
            blocked_not_checkable += 1

    per_language_metrics = {}
    for language, total in sorted(language_total.items()):
        lang_correct = language_correct[language]
        lang_neutral = language_neutral[language]
        per_language_metrics[language] = {
            "total_claims": total,
            "correct_predictions": lang_correct,
            "accuracy": round(lang_correct / total, 3) if total else 0.0,
            "neutral_rate": round(lang_neutral / total, 3) if total else 0.0,
            "failed_predictions": failed_by_language[language],
        }

    metrics = {
        "total_claims": len(results),
        "correct_predictions": correct,
        "accuracy": round(correct / len(results), 3) if results else 0.0,
        "neutral_rate": round(neutral / len(results), 3) if results else 0.0,
        "blocked_not_checkable_count": blocked_not_checkable,
        "actual_positive": actual_positive,
        "actual_negative": actual_negative,
        "predicted_positive": predicted_positive,
        "predicted_negative": predicted_negative,
        "binary_ground_truth_total": binary_total,
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "false_positive_rate": round(fp / binary_total, 3) if binary_total else 0.0,
        "false_negative_rate": round(fn / binary_total, 3) if binary_total else 0.0,
        "label_confusion_matrix": {truth: dict(row) for truth, row in confusion.items()},
        "failed_by_expected_verdict": dict(failed_by_expected),
        "failed_by_predicted_verdict": dict(failed_by_predicted),
        "failed_by_language": dict(failed_by_language),
        "per_language_metrics": per_language_metrics,
        "failed_claims": failed_claims,
    }
    return metrics


async def main():
    parser = argparse.ArgumentParser(description="Run the Indian-language benchmark.")
    parser.add_argument("--claims-file", default=None, help="Optional JSON file with {language, claim, expected_verdict} rows.")
    parser.add_argument("--output", default="indian_language_benchmark_results.json", help="Output JSON path.")
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
    output = {
        "benchmark_metrics": metrics,
        "total_time_seconds": total_time,
        "average_claim_time": round(sum(claim_times) / len(claim_times), 3) if claim_times else 0.0,
        "claim_results": results,
    }

    Path(args.output).write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n==============================")
    print("BENCHMARK METRICS")
    print("==============================")
    for k, v in metrics.items():
        if k in {"label_confusion_matrix", "failed_claims", "per_language_metrics"}:
            continue
        print(f"{k} : {v}")
    print("per_language_metrics :", metrics.get("per_language_metrics"))
    print("\nResults saved to", args.output)


if __name__ == "__main__":
    asyncio.run(main())
