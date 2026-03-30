import asyncio
import json
from pipeline.document_pipeline import DocumentPipeline


claims = [

    "The earth is flat",
    "Vaccines cause autism",
    "China has the largest population in the world",
    "The capital of France is Paris",
    "India is the largest economy in the world",
    "The blue color of the sky is caused by Rayleigh scattering",
    "The Sahara is the largest desert in the world",
    "Mount Everest is the tallest mountain on Earth",
]


async def run_batch():

    pipeline = DocumentPipeline()

    results = []

    for i, claim in enumerate(claims, 1):

        print("\n===========================")
        print(f"Processing claim {i}/{len(claims)}")
        print("Claim:", claim)

        result = await pipeline._process_text(claim)

        results.append(result)

        print("Verdict:", result["document_verdict"])

    with open("batch_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print("\nBatch processing complete.")
    print("Results saved to batch_results.json")


if __name__ == "__main__":

    asyncio.run(run_batch())