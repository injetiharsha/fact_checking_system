#!/usr/bin/env python
import asyncio
import sys
import traceback

try:
    from pipeline.document_pipeline import DocumentPipeline
    print("✓ Imports successful")
    
    pipeline = DocumentPipeline()
    print("✓ Pipeline created")
    
    text = 'The Sky is Blue'
    print(f"✓ Running test with text: {text}")
    
    res = asyncio.run(pipeline._process_text(
        text, 
        source_url='https://en.wikipedia.org/wiki/Sky'
    ))
    
    print("✓ Pipeline executed successfully")
    print(f"Result: {res}")
    
except Exception as e:
    print(f"✗ Error: {type(e).__name__}: {e}")
    traceback.print_exc()
    sys.exit(1)
