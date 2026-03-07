import asyncio
import json
import time

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
    false_positive = 0
    neutral = 0

    for r in results:

        pred = r["predicted_verdict"]
        truth = r["expected_verdict"]

        if pred == truth:
            correct += 1

        if pred == "TRUE" and truth == "FALSE":
            false_positive += 1

        if pred == "NEUTRAL":
            neutral += 1

    total = len(results)

    return {
        "total_claims": total,
        "correct_predictions": correct,
        "accuracy": round(correct / total, 3),
        "false_positive_rate": round(false_positive / total, 3),
        "neutral_rate": round(neutral / total, 3)
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

    for k,v in metrics.items():
        print(k,":",v)

    save_results(results, metrics, claim_times, total_time)


if __name__ == "__main__":
    asyncio.run(main())