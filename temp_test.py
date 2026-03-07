from pipeline.document_pipeline import DocumentPipeline

pipeline = DocumentPipeline()
print('created')
res = pipeline._process_text('Test claim', source_url='http://example.com')
print('result:', res)
