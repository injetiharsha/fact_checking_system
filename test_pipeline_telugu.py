from pipeline.document_pipeline import DocumentPipeline
import json
import asyncio

async def main():
    pipeline = DocumentPipeline()
    print("=== DOCUMENT PIPELINE TEST (TELUGU IMAGE) ===")
    print(f"Image: F:\\fact_checking_system\\test_images\\telugu\\image1.png\n")
    
    result = await pipeline.process_image(
        r"F:\fact_checking_system\test_images\telugu\image1.png",
        cancel_event=asyncio.Event()
    )
    
    print("Result:")
    print(json.dumps(result, indent=2, ensure_ascii=False))

asyncio.run(main())
