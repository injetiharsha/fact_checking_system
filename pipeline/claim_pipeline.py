import time
import asyncio
import nltk
import json
import sys
from evidence.router import EvidenceRouter
from evidence.relevance import RelevanceScorer
from evidence.quality import QualityScorer
from evidence.citation_formatter import format_citations
from semantic.stance_model import StanceDetector

from reasoning.logical_analyzer import LogicalAnalyzer
from reasoning.logic_engine import LogicEngine
from reasoning.rank_reasoner import numeric_rank_reasoning
from reasoning.year_reasoner import year_reasoning
from reasoning.contradiction_detector import ConflictAnalyzer

from verdict.aggregate import aggregate_results
from verdict.explanation_generator import generate_explanation

from nlp.language import detect_language
from nlp.translate import translate_to_english
from claim_detection.normalizer import normalize_claim
from claim_detection.claim_type_classifier import ClaimTypeClassifier
from evidence.domain_diversity_filter import DomainDiversityFilter

try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    nltk.download("punkt", quiet=True)


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

    def _safe_console_text(value):
        out = str(value)
        enc = getattr(sys.stdout, "encoding", None) or "utf-8"
        return out.encode(enc, errors="replace").decode(enc, errors="replace")

    print("\n--- Sentence candidates ---")
    for s in sentences[:5]:
        print("-", _safe_console_text(s[:120]))

    print("Selected:", _safe_console_text(best_sentence))

    return best_sentence


# ----------------------------------------------------------
# Claim Pipeline
# ----------------------------------------------------------

class ClaimPipeline:

    def __init__(self):

        # initialize core components
        self.router = EvidenceRouter()
        self.logical_analyzer = LogicalAnalyzer()
        self.claim_type_classifier = ClaimTypeClassifier()
        self.domain_diversity_filter = DomainDiversityFilter(max_per_domain=2)
        self.relevance_scorer = RelevanceScorer()
        self.quality_scorer = QualityScorer()
        self.stance = StanceDetector()
        self.logic_engine = LogicEngine()
        self.conflict_analyzer = ConflictAnalyzer()
        self.strong_relevance_threshold = 0.45
        self.strong_quality_threshold = 0.4
        self.soft_relevance_threshold = 0.3
        self.soft_quality_threshold = 0.25
        self.min_strong_evidence_for_forced_verdict = 1

    def _build_transparency(
        self,
        claim_type_result,
        language,
        evidence_retrieved,
        evidence_cleaned,
        scored_evidence,
        results,
        strong_evidence_count,
        forced_neutral,
        logic_engine_injected,
    ):
        stance_source_counts = {}
        for item in results:
            source = str(item.get("stance_source") or "unknown")
            stance_source_counts[source] = stance_source_counts.get(source, 0) + 1

        support_count = sum(1 for item in results if item.get("stance") == "SUPPORT")
        refute_count = sum(1 for item in results if item.get("stance") == "REFUTE")
        neutral_count = sum(1 for item in results if item.get("stance") == "NEUTRAL")

        soft_evidence_count = sum(
            1 for item in scored_evidence if item.get("evidence_tier") == "soft"
        )

        return {
            "version": "phase6-v1",
            "language_detected": language,
            "claim_type": {
                "label": claim_type_result["type"].value,
                "confidence": round(float(claim_type_result.get("confidence", 0.0)), 3),
                "decision_source": claim_type_result.get("decision_source", "unknown"),
            },
            "thresholds": {
                "strong_relevance": self.strong_relevance_threshold,
                "strong_quality": self.strong_quality_threshold,
                "soft_relevance": self.soft_relevance_threshold,
                "soft_quality": self.soft_quality_threshold,
                "min_strong_evidence_for_definitive_verdict": self.min_strong_evidence_for_forced_verdict,
            },
            "evidence_stats": {
                "retrieved": evidence_retrieved,
                "cleaned": evidence_cleaned,
                "scored": len(scored_evidence),
                "strong": strong_evidence_count,
                "soft": soft_evidence_count,
                "support": support_count,
                "refute": refute_count,
                "neutral": neutral_count,
            },
            "stance_sources": stance_source_counts,
            "policy_flags": {
                "forced_neutral_due_to_weak_evidence": forced_neutral,
                "logic_engine_injected": logic_engine_injected,
            },
        }

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

        # classify claim type (FACTUAL, OPINION, NUMERICAL, MIXED)
        start = time.time()
        claim_type_result = self.claim_type_classifier.classify(claim)
        trace["claim_type"] = {
            **claim_type_result,
            "type": claim_type_result["type"].value,
        }
        print(f"Claim type: {claim_type_result['type'].value} (confidence: {claim_type_result['confidence']:.2f})")
        print("Claim type classification:", round(time.time() - start, 3), "sec")

        # extract domain to exclude original source
        exclude_domain = None
        if source_url:
            exclude_domain = source_url.split("/")[2].replace("www.", "")

        # retrieve evidence from router
        start = time.time()
        try:
            evidence_raw = await self.router.get_evidence(
                claim,
                exclude_domain=exclude_domain
            )
        except asyncio.CancelledError:
            return {
                "claim": claim,
                "language": language,
                "evidence": [],
                "final_verdict": "NEUTRAL",
                "confidence": 0.0,
                "conflict_analysis": "Request cancelled during server reload/shutdown",
                "citations": [],
                "logical_analysis": logic_metadata,
                "explanation": "Request was cancelled before evidence retrieval completed.",
                "transparency": {
                    "version": "phase6-v1",
                    "language_detected": language,
                    "status": "cancelled_during_evidence_retrieval",
                },
            }

        evidence_retrieved_count = len(evidence_raw)

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
        evidence_cleaned_count = len(evidence_raw)

        # compute relevance and quality scores
        start = time.time()

        scored_evidence = []
        strong_evidence_count = 0

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

            evidence_tier = None
            adjusted_weight = ev["weight"]

            if (
                relevance_score >= self.strong_relevance_threshold
                and quality_score >= self.strong_quality_threshold
            ):
                evidence_tier = "strong"
                strong_evidence_count += 1
            elif (
                relevance_score >= self.soft_relevance_threshold
                and quality_score >= self.soft_quality_threshold
            ):
                evidence_tier = "soft"
                adjusted_weight = round(ev["weight"] * 0.8, 3)
            else:
                print("Rejected evidence")
                continue

            print(f"Accepted evidence ({evidence_tier})")

            scored_evidence.append({
                "source": ev["source"],
                "url": ev["url"],
                "text": best_sentence,
                "weight": adjusted_weight,
                "raw_weight": ev["weight"],
                "relevance_score": relevance_score,
                "quality_score": quality_score,
                "combined_score": round(relevance_score * quality_score, 4),
                "evidence_tier": evidence_tier,
            })

            # store selected evidence in trace
            trace["evidence_selected"].append({
                "url": ev["url"],
                "sentence": best_sentence,
                "relevance": relevance_score,
                "quality": quality_score
            })

        # abstain early if no evidence passes filtering
        if not scored_evidence:
            print("No usable evidence found - abstaining")
            return {
                "claim": claim,
                "language": language,
                "evidence": [],
                "final_verdict": "NEUTRAL",
                "confidence": 0.45,
                "conflict_analysis": "Insufficient evidence",
                "citations": [],
                "logical_analysis": logic_metadata,
                "explanation": "No sufficiently relevant and high-quality evidence was found.",
                "transparency": self._build_transparency(
                    claim_type_result=claim_type_result,
                    language=language,
                    evidence_retrieved=evidence_retrieved_count,
                    evidence_cleaned=evidence_cleaned_count,
                    scored_evidence=[],
                    results=[],
                    strong_evidence_count=0,
                    forced_neutral=True,
                    logic_engine_injected=False,
                ),
            }

        # sort evidence by combined score
        scored_evidence.sort(
            key=lambda x: x["relevance_score"] * x["quality_score"],
            reverse=True
        )

        # apply domain diversity filter - ensure evidence from diverse sources
        start_diversity = time.time()
        scored_evidence = self.domain_diversity_filter.filter(scored_evidence)
        diversity_score = self.domain_diversity_filter.get_diversity_score(scored_evidence)
        print(f"Domain diversity filter - score: {diversity_score:.2f}")
        print("Domain diversity filtering:", round(time.time() - start_diversity, 3), "sec")

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
                "raw_weight": ev.get("raw_weight", ev["weight"]),
                "stance": stance_result["stance"],
                "confidence": stance_result["confidence"],
                "stance_source": stance_result.get("source", "model"),
                "relevance_score": ev["relevance_score"],
                "quality_score": ev["quality_score"],
                "combined_score": ev.get("combined_score"),
                "evidence_tier": ev.get("evidence_tier", "soft"),
            })

            # store stance result in trace
            trace["stance_predictions"].append({
                "url": ev["url"],
                "stance": stance_result["stance"],
                "confidence": stance_result["confidence"],
                "source": stance_result.get("source", "model")
            })

        print("Semantic + NLI:", round(time.time() - start, 3), "sec")

        # logic engine reasoning pass
        logic_verdict = self.logic_engine.analyze(claim, results)
        non_neutral = [r for r in results if r.get("stance") in {"SUPPORT", "REFUTE"}]
        logic_engine_injected = False
        if (
            logic_verdict in {"SUPPORT", "REFUTE"}
            and len(non_neutral) >= 2
            and strong_evidence_count >= self.min_strong_evidence_for_forced_verdict
        ):
            results.append({
                "source": "logic_engine",
                "url": "internal://logic_engine",
                "text": "Structured reasoning signal",
                "weight": 0.8,
                "stance": logic_verdict,
                "confidence": 0.8,
                "relevance_score": 1.0,
                "quality_score": 1.0
            })
            logic_engine_injected = True

        # aggregate final verdict
        start = time.time()

        verdict, confidence = aggregate_results(results)
        conflict_summary = self.conflict_analyzer.analyze(results)

        # Abstain when there is no reliable non-neutral signal.
        forced_neutral = False
        non_neutral_count = len([r for r in results if r.get("stance") in {"SUPPORT", "REFUTE"}])
        if (
            strong_evidence_count < self.min_strong_evidence_for_forced_verdict
            or non_neutral_count == 0
        ):
            verdict = "NEUTRAL"
            confidence = min(confidence, 0.55)
            conflict_summary = "Insufficient decisive evidence for definitive verdict"
            forced_neutral = True

        citations = format_citations(results)

        explanation = generate_explanation(
            claim,
            results,
            verdict,
            confidence,
            conflict_summary=conflict_summary,
        )

        transparency = self._build_transparency(
            claim_type_result=claim_type_result,
            language=language,
            evidence_retrieved=evidence_retrieved_count,
            evidence_cleaned=evidence_cleaned_count,
            scored_evidence=scored_evidence,
            results=results,
            strong_evidence_count=strong_evidence_count,
            forced_neutral=forced_neutral,
            logic_engine_injected=logic_engine_injected,
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
            "explanation": explanation,
            "transparency": transparency,
        }


