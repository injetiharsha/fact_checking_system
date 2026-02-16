# pipeline/claim_pipeline.py

from reasoning.contradiction_detector import analyze_conflict
from evidence.citation_formatter import format_citations
from reasoning.rank_reasoner import numeric_rank_reasoning
from reasoning.year_reasoner import year_reasoning
from semantic.retriever import SemanticRetriever
from semantic.stance_model import StanceDetector
from semantic.sentence_highlighter import SentenceHighlighter

from verdict.aggregate import aggregate_results
from verdict.explanation_generator import generate_explanation

from evidence.router import EvidenceRouter


class ClaimPipeline:

    def __init__(self):
        self.retriever = SemanticRetriever()
        self.stance = StanceDetector()
        self.highlighter = SentenceHighlighter()
        self.router = EvidenceRouter()

    def run(self, claim, source_url=None):

        exclude_domain = None

        if source_url:
            exclude_domain = source_url.split("/")[2].replace("www.", "")

        evidence_raw = self.router.get_evidence(
            claim,
            exclude_domain=exclude_domain
        )

        results = []

        for ev in evidence_raw:
            top_sentences = self.retriever.get_top_sentences(claim, ev["text"])
            if not top_sentences:
                continue

            highlighted = " ".join(top_sentences)

            year_check = year_reasoning(claim, highlighted)

            if year_check:
                stance_result = {
                    "stance": year_check,
                    "confidence": 0.95
                }
            else:
                numeric_stance = numeric_rank_reasoning(claim, highlighted)

                if numeric_stance:
                    stance_result = {
                        "stance": numeric_stance,
                        "confidence": 0.99
                    }
                else:
                    stance_result = self.stance.detect(claim, highlighted)

            results.append({
                "source": ev["source"],
                "url": ev["url"],
                "text": highlighted,
                "weight": ev["weight"],
                "stance": stance_result["stance"],
                "confidence": stance_result["confidence"]
            })

        verdict, confidence = aggregate_results(results)

        conflict_summary = analyze_conflict(results)
        citations = format_citations(results)
        explanation = generate_explanation(
            claim,
            results,
            verdict,
            confidence
        )

        return {
            "claim": claim,
            "evidence": results,
            "final_verdict": verdict,
            "confidence": confidence,
            "conflict_analysis": conflict_summary,
            "citations": citations,
            "explanation": explanation
        }
