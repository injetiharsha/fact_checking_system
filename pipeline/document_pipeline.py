from ingestion.webpage import WebpageIngestor
from ingestion.pdf import extract_pdf
from ingestion.image import extract_image_text

from claim_detection.extractor import ClaimExtractor
from pipeline.claim_pipeline import ClaimPipeline
from verdict.document_scorer import score_document


class DocumentPipeline:

    def __init__(self):
        self.web_ingestor = WebpageIngestor()
        self.extractor = ClaimExtractor()
        self.claim_pipeline = ClaimPipeline()

    def run(self, url):
        text = self.web_ingestor.extract_text(url)
        return self._process_text(text, source_url=url)

    def process_pdf(self, file_path):
        text = extract_pdf(file_path)
        return self._process_text(text)

    def process_image(self, file_path):
        text = extract_image_text(file_path)
        return self._process_text(text)

    def _process_text(self, text, source_url=None):

        if not text:
            return {"error": "Could not extract text"}

        claims = self.extractor.extract_claims(text)

        results = []

        for claim in claims:
            claim_result = self.claim_pipeline.run(
                claim,
                source_url=source_url
            )
            results.append(claim_result)

        document_score = score_document(results)

        return {
            "source_url": source_url,
            "claims_analyzed": len(results),
            "true_claims": document_score["true"],
            "false_claims": document_score["false"],
            "neutral_claims": document_score["neutral"],
            "document_credibility_score": document_score["score"],
            "document_verdict": document_score["verdict"],
            "results": results
        }
