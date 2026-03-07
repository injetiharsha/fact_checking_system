import asyncio
from pipeline.document_pipeline import DocumentPipeline
from evidence.router import EvidenceRouter


async def debug_pipeline(claim):

    print("\n==============================")
    print("CLAIM:", claim)
    print("==============================\n")

    router = EvidenceRouter()

    print("STEP 1: Retrieving evidence\n")

    evidence = await router.get_evidence(claim)

    print(f"\nEvidence retrieved: {len(evidence)} sources\n")

    for i, ev in enumerate(evidence[:5], 1):

        print("----- Evidence", i, "-----")
        print("Source:", ev["source"])
        print("URL:", ev["url"])
        print("Weight:", ev["weight"])
        print("Text preview:", ev["text"][:200])
        print()

    print("\nSTEP 2: Running full pipeline\n")

    pipeline = DocumentPipeline()

    result = await pipeline._process_text(claim)

    print("\nFINAL RESULT\n")
    print(result)


if __name__ == "__main__":

    claim = input("Enter claim: The earth is flat ")

    asyncio.run(debug_pipeline(claim))