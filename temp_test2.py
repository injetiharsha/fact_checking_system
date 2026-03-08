import asyncio
import json
from pipeline.document_pipeline import DocumentPipeline

pipeline = DocumentPipeline()

claim = "The Earth is Flat" \
""

print("Claim length:", len(claim.split()))

result = asyncio.run(pipeline._process_text(claim))

print(json.dumps(result, indent=1))