import asyncio
import json
from pipeline.document_pipeline import DocumentPipeline

pipeline = DocumentPipeline()

claim = "India is the top 1 largest economy in the world" \
""

print("Claim length:", len(claim.split()))

result = asyncio.run(pipeline._process_text(claim))

print(json.dumps(result, indent=1))