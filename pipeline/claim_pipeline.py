import time
import nltk
import json
from evidence.router import EvidenceRouter
from evidence.relevance import RelevanceScorer
from evidence.quality import QualityScorer
from evidence.citation_formatter import format_citations
from utils.pipeline_trace import PipelineTrace
from semantic.stance_model import StanceDetector

from reasoning.logical_analyzer import LogicalAnalyzer
from reasoning.rank_reasoner import numeric_rank_reasoning
from reasoning.year_reasoner import year_reasoning
from reasoning.contradiction_detector import ConflictAnalyzer

from verdict.aggregate import aggregate_results
from verdict.explanation_generator import generate_explanation

from nlp.language import detect_language
from nlp.translate import translate_to_english
from claim_detection.normalizer import normalize_claim

nltk.download("punkt")


# ----------------------------------------------------------
# Sentence Extraction
# ----------------------------------------------------------

def extract_best_sentence(claim, text, relevance_scorer):

    if not text:
        return None

    sentences = nltk.sent_tokenize(text)

    if not sentences:
        return None

    claim_words = set(claim.lower().split())

    best_sentence = None
    best_score = 0

    for sent in sentences:

        sent = sent.strip()
        words = sent.split()

        if len(words) < 6 or len(words) > 80:
            continue

        score = relevance_scorer.score(claim, sent)

        overlap = len(claim_words & set(sent.lower().split()))
        score += overlap * 0.05

        if score > best_score:
            best_score = score
            best_sentence = sent

    print("\n--- Sentence candidates ---")
    for s in sentences[:5]:
        print("-", s[:120])

    print("Selected:", best_sentence)

    return best_sentence


# ----------------------------------------------------------
# Claim Pipeline
# ----------------------------------------------------------

class ClaimPipeline:

    def __init__(self):

        # initialize core components
        self.router = EvidenceRouter()
        self.logical_analyzer = LogicalAnalyzer()
        self.relevance_scorer = RelevanceScorer()
        self.quality_scorer = QualityScorer()
        self.stance = StanceDetector()
        self.conflict_analyzer = ConflictAnalyzer()

    async def run(self, claim, source_url=None):

        # trace object for debugging pipeline flow
        trace = {
            "claim": claim,
            "search_results": [],
            "scraped_pages": [],
            "evidence_selected": [],
            "stance_predictions": [],
            "final_verdict": None
        }

        total_start = time.time()

        print("\n==============================")
        print("Processing claim:", claim)

        # run logical claim analysis
        start = time.time()
        logic_metadata = self.logical_analyzer.analyze(claim)
        print("Logical analyzer:", round(time.time() - start, 3), "sec")

        # detect language and normalize claim
        start = time.time()
        language = detect_language(claim)
        claim = translate_to_english(claim, language)
        claim = normalize_claim(claim)
        print("Language + normalization:", round(time.time() - start, 3), "sec")

        # extract domain to exclude original source
        exclude_domain = None
        if source_url:
            exclude_domain = source_url.split("/")[2].replace("www.", "")

        # retrieve evidence from router
        start = time.time()
        evidence_raw = await self.router.get_evidence(
            claim,
            exclude_domain=exclude_domain
        )

        # store search results in trace
        for ev in evidence_raw:
            trace["search_results"].append({
                "source": ev.get("source"),
                "url": ev.get("url")
            })

        print("Evidence retrieved:", len(evidence_raw))
        print("Evidence retrieval:", round(time.time() - start, 3), "sec")

        # clean weak or irrelevant evidence
        cleaned = []
        for ev in evidence_raw:

            text = ev.get("text")

            if not text:
                continue

            if len(text.split()) < 20:
                continue

            if "search" in text.lower():
                continue

            cleaned.append(ev)

        if cleaned:
            evidence_raw = cleaned

        print("Cleaned evidence:", len(evidence_raw))

        # compute relevance and quality scores
        start = time.time()

        scored_evidence = []

        for ev in evidence_raw:

            print("\nChecking source:", ev["source"])
            print("URL:", ev["url"])

            # skip low credibility sources
            if ev["weight"] < 0.2:
                print("Rejected (low credibility)")
                continue

            text = ev.get("text")
            if not text:
                continue

            # extract best sentence from document
            best_sentence = extract_best_sentence(
                claim,
                text,
                self.relevance_scorer
            )

            if not best_sentence:
                continue

            # compute scores
            relevance_score = self.relevance_scorer.score(claim, best_sentence)
            quality_score = self.quality_scorer.score(best_sentence)

            print("Relevance:", relevance_score)
            print("Quality:", quality_score)

            # reject weak evidence
            if relevance_score < 0.35 or quality_score < 0.3:
                print("Rejected evidence")
                continue

            print("Accepted evidence")

            scored_evidence.append({
                "source": ev["source"],
                "url": ev["url"],
                "text": best_sentence,
                "weight": ev["weight"],
                "relevance_score": relevance_score,
                "quality_score": quality_score
            })

            # store selected evidence in trace
            trace["evidence_selected"].append({
                "url": ev["url"],
                "sentence": best_sentence,
                "relevance": relevance_score,
                "quality": quality_score
            })

        # fallback if no evidence passes filtering
        if not scored_evidence:

            print("No strong evidence found — using fallback")

            for ev in evidence_raw[:5]:

                text = ev.get("text", "")

                scored_evidence.append({
                    "source": ev["source"],
                    "url": ev["url"],
                    "text": text[:300],
                    "weight": ev["weight"],
                    "relevance_score": 0.2,
                    "quality_score": 0.2
                })

        # sort evidence by combined score
        scored_evidence.sort(
            key=lambda x: x["relevance_score"] * x["quality_score"],
            reverse=True
        )

        scored_evidence = scored_evidence[:5]

        print("Relevance + quality:", round(time.time() - start, 3), "sec")

        # run stance detection
        start = time.time()

        results = []

        for ev in scored_evidence:

            highlighted = ev["text"]

            print("\nSTANCE CHECK")
            print("Evidence:", highlighted)

            stance_result = None

            # apply year reasoning
            year_check = year_reasoning(claim, highlighted)

            if year_check:
                stance_result = {"stance": year_check, "confidence": 0.95}

            else:

                # apply rank reasoning
                rank_check = numeric_rank_reasoning(claim, highlighted)

                if rank_check:
                    stance_result = {"stance": rank_check, "confidence": 0.99}

                else:
                    stance_result = self.stance.detect(highlighted, claim)

            print("Stance:", stance_result)

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

            # store stance result in trace
            trace["stance_predictions"].append({
                "url": ev["url"],
                "stance": stance_result["stance"],
                "confidence": stance_result["confidence"]
            })

        print("Semantic + NLI:", round(time.time() - start, 3), "sec")

        # aggregate final verdict
        start = time.time()

        verdict, confidence = aggregate_results(results)
        conflict_summary = self.conflict_analyzer.analyze(results)
        citations = format_citations(results)

        explanation = generate_explanation(
            claim,
            results,
            verdict,
            confidence
        )

        trace["final_verdict"] = {
            "verdict": verdict,
            "confidence": confidence
        }

        print("\n========== FINAL RESULT ==========")
        print("Verdict:", verdict)
        print("Confidence:", confidence)
        print("Conflict:", conflict_summary)

        print("Aggregation:", round(time.time() - start, 3), "sec")
        print("TOTAL PIPELINE TIME:", round(time.time() - total_start, 3), "sec")


        trace["final_verdict"] = {
    "verdict": verdict,
    "confidence": confidence
}
        with open("pipeline_trace.json", "w", encoding="utf-8") as f:
            json.dump(trace, f, indent=2)

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