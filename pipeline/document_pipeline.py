from ingestion.webpage import WebpageIngestor
from claim_detection.extractor import ClaimExtractor
from pipeline.claim_pipeline import ClaimPipeline
from verdict.document_scorer import score_document


class DocumentPipeline:

    def __init__(self):
        self.ingestor = WebpageIngestor()
        self.extractor = ClaimExtractor()
        self.claim_pipeline = ClaimPipeline()

    def run(self, url):
        text = self.ingestor.extract_text(url)

        claims = self.extractor.extract_claims(text)

        results = []

        for claim in claims:
            claim_result = self.claim_pipeline.run(
                claim,
                source_url=url
            )
            results.append(claim_result)

        document_score = score_document(results)

        return {
            "source_url": url,
            "claims_analyzed": len(results),
            "true_claims": document_score["true"],
            "false_claims": document_score["false"],
            "neutral_claims": document_score["neutral"],
            "document_credibility_score": document_score["score"],
            "document_verdict": document_score["verdict"],
            "results": results
        }
