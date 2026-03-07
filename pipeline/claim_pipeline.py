# pipeline/claim_pipeline.py

import time

from reasoning.contradiction_detector import analyze_conflict
from evidence.citation_formatter import format_citations
from reasoning.rank_reasoner import numeric_rank_reasoning
from reasoning.year_reasoner import year_reasoning

from semantic.retriever import SemanticRetriever
from semantic.stance_model import StanceDetector

from nlp.language import detect_language
from claim_detection.normalizer import normalize_claim
from verdict.aggregate import aggregate_results
from verdict.explanation_generator import generate_explanation
from nlp.translate import translate_to_english

from evidence.router import EvidenceRouter
from reasoning.logical_analyzer import LogicalAnalyzer
from evidence.relevance import RelevanceScorer
from evidence.quality import QualityScorer


class ClaimPipeline:

    def __init__(self):

        # Core modules
        self.router = EvidenceRouter()
        self.retriever = SemanticRetriever()
        self.stance = StanceDetector()

        # NLP tools
        self.logical_analyzer = LogicalAnalyzer()

        # Scoring tools
        self.relevance_scorer = RelevanceScorer()
        self.quality_scorer = QualityScorer()

    async def run(self, claim, source_url=None):

        total_start = time.time()

        # -----------------------------
        # 1️⃣ Logical Analysis
        # -----------------------------

        t1 = time.time()
        logic_metadata = self.logical_analyzer.analyze(claim)
        print("Logical analyzer:", round(time.time() - t1, 3), "sec")

        # -----------------------------
        # 2️⃣ Language + Normalization
        # -----------------------------

        t2 = time.time()

        language = detect_language(claim)
        claim = translate_to_english(claim, language)
        claim = normalize_claim(claim)

        print("Language + normalization:", round(time.time() - t2, 3), "sec")

        # -----------------------------
        # 3️⃣ Domain exclusion
        # -----------------------------

        exclude_domain = None

        if source_url:
            exclude_domain = source_url.split("/")[2].replace("www.", "")

        # -----------------------------
        # 4️⃣ Evidence Retrieval
        # -----------------------------

        t3 = time.time()

        evidence_raw = await self.router.get_evidence(
            claim,
            exclude_domain=exclude_domain
        )

        print("Evidence retrieval:", round(time.time() - t3, 3), "sec")

        evidence_raw = [
    ev for ev in evidence_raw
    if ev.get("text")
    and len(ev["text"].split()) > 20
    and "search" not in ev["text"].lower()
]

        # -----------------------------
        # 5️⃣ Relevance + Quality Scoring
        # -----------------------------

        t4 = time.time()

        scored_evidence = []

        for ev in evidence_raw:

            relevance_score = self.relevance_scorer.score(
                claim,
                ev["text"]
            )

            quality_score = self.quality_scorer.score(
                ev["text"]
            )

            ev["relevance_score"] = relevance_score
            ev["quality_score"] = quality_score

            # Filter weak evidence
            if relevance_score >= 0.2 and quality_score >= 0.2:
                scored_evidence.append(ev)


            if not scored_evidence:
                scored_evidence = evidence_raw[:3]

        # Sort strongest evidence first
        scored_evidence.sort(
            key=lambda x: x["relevance_score"] * x["quality_score"],
            reverse=True
        )

        # Keep top evidence for next steps

        scored_evidence = evidence_raw[:8]



        print("Relevance + quality:", round(time.time() - t4, 3), "sec")

     
        # 6️⃣ Sentence Extraction + Stance
      

        t5 = time.time()

        results = []

        for ev in scored_evidence:

            top_sentences = self.retriever.get_top_sentences(
                claim,
                ev["text"]
            )

            # fallback if extraction fails
            if not top_sentences:
                highlighted = ev["text"][:300]
            else:
                highlighted = " ".join(top_sentences)

            # -------------------------
            # Reasoning Layer
            # -------------------------

            stance_result = None

            # Year reasoning
            year_check = year_reasoning(claim, highlighted)

            if year_check:

                stance_result = {
                    "stance": year_check,
                    "confidence": 0.95
                }

            else:

                # Numeric reasoning
                numeric_check = numeric_rank_reasoning(
                    claim,
                    highlighted
                )

                if numeric_check:

                    stance_result = {
                        "stance": numeric_check,
                        "confidence": 0.99
                    }

                else:

                    # Semantic similarity shortcut
                    sim = self.relevance_scorer.score(
                        claim,
                        highlighted
                    )

                    if sim > 0.6:

                        stance_result = {
                            "stance": "SUPPORT",
                            "confidence": 0.9
                        }

                    else:

                        # Full NLI model
                        stance_result = self.stance.detect(
                            claim,
                            highlighted
                        )

            results.append({
                "source": ev["source"],
                "url": ev["url"],
                "text": highlighted,
                "weight": ev["weight"],
                "stance": stance_result["stance"],
                "confidence": stance_result["confidence"],
                "relevance_score": ev["relevance_score"],
                "quality_score": ev["quality_score"]
            })

        print("Semantic + NLI:", round(time.time() - t5, 3), "sec")

        # -----------------------------
        # 7️⃣ Aggregation
        # -----------------------------

        t6 = time.time()

        verdict, confidence = aggregate_results(results)

        conflict_summary = analyze_conflict(results)

        citations = format_citations(results)

        explanation = generate_explanation(
            claim,
            results,
            verdict,
            confidence
        )

        print("Aggregation:", round(time.time() - t6, 3), "sec")

        print(
            "TOTAL PIPELINE TIME:",
            round(time.time() - total_start, 3),
            "sec"
        )

        return {
            "claim": claim,
            "language": language,
            "evidence": results,
            "final_verdict": verdict,
            "confidence": confidence,
            "conflict_analysis": conflict_summary,
            "citations": citations,
            "logical_analysis": logic_metadata,
            "explanation": explanation
        }
    
    