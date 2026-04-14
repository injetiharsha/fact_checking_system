import time
import asyncio
import nltk
import json
import sys
import re
import os
import hashlib
import html
from urllib.parse import urlparse
from evidence.router import EvidenceRouter
try:
    from crawl4ai import crawl_claim_evidence
    CRAWL4AI_AVAILABLE = True
except ImportError:
    CRAWL4AI_AVAILABLE = False
from evidence.relevance import RelevanceScorer
from evidence.quality import QualityScorer
from evidence.citation_formatter import format_citations
from semantic.stance_model import StanceDetector
from semantic.verifier_v2 import VerifierV2
from semantic.llm_verifier import LLMVerifier

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
from claim_detection.claim_checkability import ClaimCheckabilityClassifier
from claim_detection.claim_context_classifier import ClaimContextClassifier
from evidence.domain_diversity_filter import DomainDiversityFilter
from evidence.session_retrieval_cache import SessionRetrievalCache
from evidence.index_reranker import IndexReranker
from pipeline.claim_type_utils import (
    best_numeric_pairwise_rel_diff,
    claim_type_label_lower,
    collect_non_year_numeric_values,
)

try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    nltk.download("punkt", quiet=True)


# ----------------------------------------------------------
# Sentence Extraction
# ----------------------------------------------------------

def _normalize_token(token):
    token = (token or "").lower().strip(".,;:!?()[]{}\"'")
    if token.endswith("ies") and len(token) > 4:
        return token[:-3] + "y"
    if token.endswith("es") and len(token) > 4:
        return token[:-2]
    if token.endswith("s") and len(token) > 3:
        return token[:-1]
    return token


def _token_set(text):
    tokens = set()
    for raw in (text or "").lower().split():
        normalized = _normalize_token(raw)
        if normalized:
            tokens.add(normalized)
    return tokens


def _safe_console_text(value):
    out = str(value)
    enc = getattr(sys.stdout, "encoding", None) or "utf-8"
    return out.encode(enc, errors="replace").decode(enc, errors="replace")


def _sanitize_evidence_text(text):
    cleaned = str(text or "")
    if not cleaned:
        return ""
    cleaned = html.unescape(cleaned)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _sanitize_evidence_rows(rows):
    sanitized = []
    for row in rows or []:
        item = dict(row)
        item["text"] = _sanitize_evidence_text(item.get("text", ""))
        if "context_text" in item:
            item["context_text"] = _sanitize_evidence_text(item.get("context_text", ""))
        sanitized.append(item)
    return sanitized


def _build_ux_warnings(claim):
    claim_text = " ".join((claim or "").strip().split())
    if not claim_text:
        return []

    word_count = len(claim_text.split())
    warnings = []
    if word_count <= 7 and word_count >= 5:
        warnings.append({
            "code": "short_claim",
            "message": "Short claim detected. Adding a little more context may improve search quality.",
            "word_count": word_count,
        })
    return warnings


def _relation_bonus(claim, sentence):
    claim_text = (claim or "").lower().strip()
    sent_text = (sentence or "").lower()
    bonus = 0.0

    years = re.findall(r"\b(\d{3,4})\b", claim_text)
    if years and any(year in sent_text for year in years):
        bonus += 0.05

    return bonus


def _direct_answer_bonus(claim, sentence):
    return 0.0


def _lead_position_bonus(sentence_index, total_sentences):
    if total_sentences <= 0:
        return 0.0
    if sentence_index <= 2:
        return 0.08
    if sentence_index <= 5:
        return 0.05
    if sentence_index <= 8:
        return 0.02
    return 0.0


def _claim_reporting_penalty(claim, sentence, source_name=None, context_result=None):
    return 0.0


def _metadata_or_shell_penalty(sentence, source_name=None, context_text=None):
    text = " ".join(
        part.strip().lower()
        for part in [sentence or "", context_text or "", source_name or ""]
        if str(part or "").strip()
    )
    if not text:
        return 0.0

    heavy_markers = (
        "cookie policy",
        "accept cookies",
        "privacy policy",
        "terms of use",
        "all rights reserved",
        "sign in",
        "log in",
        "subscribe",
        "newsletter",
        "follow us",
        "share this",
        "advertisement",
        "sponsored",
        "read more",
        "click here",
        "watch live",
        "live updates",
        "photo gallery",
        "image source",
        "image credit",
        "published on",
        "updated on",
        "min read",
        "breadcrumb",
    )
    medium_markers = (
        "author",
        "copyright",
        "comments",
        "menu",
        "navigation",
        "skip to content",
        "related stories",
        "related articles",
        "recommended",
        "trending",
    )
    if any(marker in text for marker in heavy_markers):
        return 0.22
    if any(marker in text for marker in medium_markers):
        return 0.1

    words = (sentence or "").split()
    if words:
        alpha_ratio = sum(ch.isalpha() for ch in (sentence or "")) / max(len(sentence or ""), 1)
        if len(words) < 8 and alpha_ratio < 0.65:
            return 0.08
    return 0.0


def _sentence_similarity(a, b):
    a_tokens = _token_set(a)
    b_tokens = _token_set(b)
    if not a_tokens or not b_tokens:
        return 0.0
    return len(a_tokens & b_tokens) / max(len(a_tokens | b_tokens), 1)


def _claim_evidence_overlap_ratio(claim, evidence):
    claim_tokens = {
        token for token in _token_set(claim)
        if len(token) > 2 and token not in {
            "the", "and", "for", "with", "from", "that", "this",
            "said", "says", "will", "would", "could", "about", "into",
            "after", "before", "during", "under", "over",
        }
    }
    evidence_tokens = _token_set(evidence)
    if not claim_tokens or not evidence_tokens:
        return 0.0
    return len(claim_tokens & evidence_tokens) / max(len(claim_tokens), 1)


def _looks_like_code_or_template_sentence(sentence):
    lowered = str(sentence or "").lower()
    if any(marker in lowered for marker in (
        "document.getelementsbytagname",
        "href.indexof(",
        "window.location",
        "queryselector(",
        "getelementbyid(",
        "addEventlistener(",
        "function(",
        "function ",
    )):
        return True
    if re.search(r"(?:^|\s)(if|for|while|function|return|var|const|let)(?:\s|\()", lowered):
        return True
    return False


def _weighted_direction_strength(row):
    confidence = float(row.get("confidence", 0.0) or 0.0)
    weight = float(row.get("weight", 0.0) or 0.0)
    source = str(row.get("stance_source") or "").lower()
    multiplier = 1.0
    if "heuristic" in source:
        multiplier *= 0.9
    if "model_low_confidence_or_neutral" in source:
        multiplier *= 0.8
    if source.startswith("model:trained_subprocess:") and confidence < 0.65:
        multiplier *= 0.9
    if source.startswith("model:") and "trained_subprocess:" not in source:
        multiplier *= 0.75
    return confidence * weight * multiplier


def _is_trusted_llm_override_source(url):
    lowered = str(url or "").lower()
    trusted_markers = (
        ".gov",
        ".gov.in",
        ".edu",
        "who.int",
        "un.org",
        "worldbank.org",
        "oecd.org",
        "rbi.org.in",
        "pib.gov.in",
        "nasa.gov",
        "jpl.nasa.gov",
        "britannica.com",
        "wikipedia.org",
        "reuters.com",
        "apnews.com",
        "bbc.com",
        "livescience.com",
        "nationalgeographic.com",
    )
    return any(marker in lowered for marker in trusted_markers)


def _select_candidates_mmr(candidates, max_sentences=3, lambda_weight=0.86):
    ranked = sorted(candidates, key=lambda item: item[1], reverse=True)
    if len(ranked) <= max_sentences:
        return ranked[:max_sentences]

    seed_pool = ranked[: min(len(ranked), 5)]
    selected = [seed_pool[0]]
    remaining = seed_pool[1:]

    while remaining and len(selected) < max_sentences:
        best_idx = 0
        best_score = None
        for idx, candidate in enumerate(remaining):
            sentence = candidate[0]
            relevance = float(candidate[1])
            redundancy = max(_sentence_similarity(sentence, chosen[0]) for chosen in selected)
            mmr_score = (lambda_weight * relevance) - ((1.0 - lambda_weight) * redundancy)
            if best_score is None or mmr_score > best_score:
                best_score = mmr_score
                best_idx = idx
        selected.append(remaining.pop(best_idx))
    return selected


def _is_official_public_admin_source(url):
    normalized = (url or "").lower().strip()
    if not normalized:
        return False
    official_markers = (
        ".gov",
        ".gov.in",
        ".gov.uk",
        ".gov.au",
        ".gov.ca",
        ".gc.ca",
        ".gouv.fr",
        ".admin.ch",
        ".europa.eu",
        ".parliament.uk",
        ".state.gov",
        ".nih.gov",
        ".cdc.gov",
        ".fda.gov",
        ".nasa.gov",
        ".who.int",
        ".un.org",
        ".oecd.org",
        ".worldbank.org",
        ".gov/",
        ".gov?",
        ".gov#",
        ".gov.",
        "nic.in",
    )
    return any(marker in normalized for marker in official_markers)

def extract_best_sentences(claim, text, relevance_scorer, max_sentences=3, source_name=None, context_result=None):

    text = _sanitize_evidence_text(text)
    if not text:
        return None

    sentences = nltk.sent_tokenize(text)

    if not sentences:
        return None

    claim_words = _token_set(claim)

    sentence_candidates = []
    seen_sentences = set()

    total_sentences = len(sentences)
    semantic_shortlist = []
    semantic_shortlist_size = max(24, max_sentences * 10)

    for sentence_index, sent in enumerate(sentences):

        sent = sent.strip()
        words = sent.split()

        if len(words) < 6 or len(words) > 80:
            continue
        if _looks_like_code_or_template_sentence(sent):
            continue

        normalized_sentence = " ".join(sent.lower().split())
        if normalized_sentence in seen_sentences:
            continue
        seen_sentences.add(normalized_sentence)

        overlap = len(claim_words & _token_set(sent))
        fast_score = relevance_scorer.fast_score(claim, sent)
        relation_bonus = _relation_bonus(claim, sent)
        direct_bonus = _direct_answer_bonus(claim, sent)
        lead_bonus = _lead_position_bonus(sentence_index, total_sentences)
        reporting_penalty = _claim_reporting_penalty(
            claim,
            sent,
            source_name=source_name,
            context_result=context_result,
        )
        context_start = max(0, sentence_index - 1)
        context_end = min(total_sentences, sentence_index + 2)
        context_text = " ".join(s.strip() for s in sentences[context_start:context_end] if s.strip())
        metadata_penalty = _metadata_or_shell_penalty(
            sent,
            source_name=source_name,
            context_text=context_text,
        )
        overlap_ratio = _claim_evidence_overlap_ratio(claim, sent)
        if overlap_ratio < 0.18 and fast_score < 0.45:
            continue
        lexical_score = (
            (fast_score * 0.96)
            + (overlap * 0.02)
            + relation_bonus
            + direct_bonus
            + lead_bonus
            - reporting_penalty
            - metadata_penalty
        )
        sentence_candidates.append(
            (
                sent,
                max(0.0, lexical_score),
                0.0,
                fast_score,
                reporting_penalty,
                metadata_penalty,
                direct_bonus,
                lead_bonus,
                context_text,
            )
        )

    if sentence_candidates:
        semantic_shortlist = sorted(sentence_candidates, key=lambda item: item[1], reverse=True)[:semantic_shortlist_size]

    rescored_candidates = []
    semantic_lookup = {}
    for sent, lexical_score, _, fast_score, reporting_penalty, metadata_penalty, direct_bonus, lead_bonus, context_text in semantic_shortlist:
        semantic_score = relevance_scorer.semantic_score(claim, sent)
        semantic_lookup[" ".join(sent.lower().split())] = semantic_score
        context_anchor = relevance_scorer.fast_score(claim, context_text) * 0.08
        combined_score = (
            (semantic_score * 0.82)
            + (fast_score * 0.14)
            + direct_bonus
            + lead_bonus
            + context_anchor
            - reporting_penalty
            - metadata_penalty
        )
        rescored_candidates.append(
            (
                sent,
                max(0.0, combined_score),
                semantic_score,
                fast_score,
                reporting_penalty,
                metadata_penalty,
                direct_bonus,
                lead_bonus,
                context_text,
            )
        )

    selected_candidates = []

    if relevance_scorer.has_trained_reranker and rescored_candidates:
        ranked = sorted(rescored_candidates, key=lambda item: item[1], reverse=True)
        shortlist = ranked[:5]
        trained_scores = relevance_scorer.score_many(claim, [item[0] for item in shortlist])
        rescored = []
        for (sent, base_score, semantic_score, fast_score, reporting_penalty, metadata_penalty, direct_bonus, lead_bonus, context_text), trained_score in zip(shortlist, trained_scores):
            combined = (
                (trained_score * 0.8)
                + (semantic_score * 0.15)
                + (fast_score * 0.05)
                + direct_bonus
                + lead_bonus
                - reporting_penalty
                - metadata_penalty
            )
            rescored.append(
                (
                    sent,
                    max(0.0, combined),
                    trained_score,
                    semantic_score,
                    fast_score,
                    reporting_penalty,
                    metadata_penalty,
                    direct_bonus,
                    lead_bonus,
                    context_text,
                )
            )
        selected_candidates = _select_candidates_mmr(rescored, max_sentences=max_sentences)
    else:
        ranked = sorted(rescored_candidates, key=lambda item: item[1], reverse=True)
        mmr_ranked = _select_candidates_mmr(ranked, max_sentences=max_sentences)
        selected_candidates = [
            (sent, score, score, semantic_score, fast_score, reporting_penalty, metadata_penalty, direct_bonus, lead_bonus, context_text)
            for sent, score, semantic_score, fast_score, reporting_penalty, metadata_penalty, direct_bonus, lead_bonus, context_text in mmr_ranked
        ]

    print("\n--- Sentence candidates ---")
    for s in sentences[:5]:
        print("-", _safe_console_text(s[:120]))

    print("Selected:")
    for sent, score, _, _, _, reporting_penalty, metadata_penalty, direct_bonus, lead_bonus, _ in selected_candidates:
        print("-", _safe_console_text(sent[:180]), f"(score={round(score,3)})")
        if reporting_penalty:
            print("  reporting penalty:", round(reporting_penalty, 3))
        if metadata_penalty:
            print("  metadata penalty:", round(metadata_penalty, 3))
        if direct_bonus:
            print("  direct answer bonus:", round(direct_bonus, 3))
        if lead_bonus:
            print("  lead bonus:", round(lead_bonus, 3))

    return [
        {
            "text": sent,
            "selector_score": round(float(score), 3),
            "reporting_penalty": round(float(reporting_penalty), 3),
            "metadata_penalty": round(float(metadata_penalty), 3),
            "direct_answer_bonus": round(float(direct_bonus), 3),
            "lead_bonus": round(float(lead_bonus), 3),
            "context_text": context_text[:800],
        }
        for sent, score, _, _, _, reporting_penalty, metadata_penalty, direct_bonus, lead_bonus, context_text in selected_candidates
    ]


# ----------------------------------------------------------
# Claim Pipeline
# ----------------------------------------------------------

class ClaimPipeline:


    def __init__(self):
        print("\n[Pipeline Feature/Model Loadout]")
        print(f"ENABLE_TRAINED_STANCE: {os.getenv('ENABLE_TRAINED_STANCE')}")
        print(f"ENABLE_TRAINED_RELEVANCE: {os.getenv('ENABLE_TRAINED_RELEVANCE')}")
        print(f"ENABLE_TRAINED_CLAIM_CHECKABILITY: {os.getenv('ENABLE_TRAINED_CLAIM_CHECKABILITY')}")
        print(f"ENABLE_TRAINED_CONTEXT: {os.getenv('ENABLE_TRAINED_CONTEXT')}")
        print(f"ENABLE_TRAINED_CLAIM_TYPE: {os.getenv('ENABLE_TRAINED_CLAIM_TYPE')}")
        print(f"ENABLE_RETRIEVAL_V2: {os.getenv('ENABLE_RETRIEVAL_V2')}")
        print(f"ENABLE_VERIFIER_V2: {os.getenv('ENABLE_VERIFIER_V2')}")
        print(f"ENABLE_LLM_VERIFIER: {os.getenv('ENABLE_LLM_VERIFIER')}")
        print(f"STANCE_CHECKPOINT: {os.getenv('STANCE_CHECKPOINT')}")
        print(f"RELEVANCE_CHECKPOINT: {os.getenv('RELEVANCE_CHECKPOINT')}")
        print(f"CLAIM_CHECKABILITY_CHECKPOINT: {os.getenv('CLAIM_CHECKABILITY_CHECKPOINT')}")
        print(f"CONTEXT_CHECKPOINT: {os.getenv('CONTEXT_CHECKPOINT')}")
        print(f"CLAIM_TYPE_CHECKPOINT: {os.getenv('CLAIM_TYPE_CHECKPOINT')}")
        print(f"LLM_VERIFIER_MODEL: {os.getenv('LLM_VERIFIER_MODEL')}")
        print("[End Pipeline Feature Print]\n")

        # initialize core components
        self.router = EvidenceRouter()
        self.logical_analyzer = LogicalAnalyzer()
        self.claim_type_classifier = ClaimTypeClassifier()
        self.claim_checkability = ClaimCheckabilityClassifier()
        self.claim_context_classifier = ClaimContextClassifier()
        self.domain_diversity_filter = DomainDiversityFilter(max_per_domain=2)
        self.quality_scorer = QualityScorer()
        self._relevance_scorer = None
        self._retrieval_v2 = None
        self._stance = None
        self._verifier_v2 = None
        self._llm_verifier = None
        self._index_reranker = None
        self._sentence_cache = {}
        self._session_retrieval_cache = SessionRetrievalCache()
        self._document_source_evidence_cache = {}
        self.logic_engine = LogicEngine()
        self.conflict_analyzer = ConflictAnalyzer()
        self.strong_relevance_threshold = 0.45
        self.strong_quality_threshold = 0.4
        self.soft_relevance_threshold = 0.3
        self.soft_quality_threshold = 0.25
        self.min_strong_evidence_for_forced_verdict = 1
        self.single_source_decisive_confidence = 0.8
        self.single_source_min_weight = 0.65
        self.soft_consensus_min_items = 3
        self.soft_consensus_min_avg_confidence = 0.85
        self.soft_consensus_min_avg_weight = 0.5
        self.soft_directional_min_items = 2
        self.soft_directional_min_avg_confidence = 0.94
        self.soft_directional_min_avg_weight = 0.4
        self.soft_directional_min_total_weight = 0.8
        self.enable_retrieval_v2 = os.getenv("ENABLE_RETRIEVAL_V2", "0").strip().lower() in {"1", "true", "yes", "on"}
        self.enable_verifier_v2 = os.getenv("ENABLE_VERIFIER_V2", "0").strip().lower() in {"1", "true", "yes", "on"}
        self.enable_llm_verifier = os.getenv("ENABLE_LLM_VERIFIER", "0").strip().lower() in {"1", "true", "yes", "on"}
        self.enable_neutral_expanded_retry = os.getenv("ENABLE_NEUTRAL_EXPANDED_RETRY", "0").strip().lower() in {"1", "true", "yes", "on"}
        self.include_verbose_api_fields = os.getenv("API_INCLUDE_VERBOSE_FIELDS", "1").strip().lower() in {"1", "true", "yes", "on"}
        self.enable_crawl4ai = os.getenv("ENABLE_CRAWL4AI", "1").strip().lower() in {"1", "true", "yes", "on"} and CRAWL4AI_AVAILABLE
        self.enable_session_cache_short_circuit = os.getenv("ENABLE_SESSION_CACHE_SHORT_CIRCUIT", "1").strip().lower() in {"1", "true", "yes", "on"}
        self.enable_index_rerank_experiment = os.getenv("ENABLE_INDEX_RERANK_EXPERIMENT", "0").strip().lower() in {"1", "true", "yes", "on"}
        self.session_cache_short_circuit_min_similarity = float(os.getenv("SESSION_CACHE_SHORT_CIRCUIT_MIN_SIMILARITY", "0.82"))
        self.default_search_cap = max(8, min(25, self._safe_env_int("CLAIM_PIPELINE_DEFAULT_SEARCH_CAP", 16)))
        self.max_search_cap = max(self.default_search_cap, min(40, self._safe_env_int("CLAIM_PIPELINE_MAX_SEARCH_CAP", 30)))
        self.retrieval_v2_candidate_sentences_per_doc = max(4, min(16, self._safe_env_int("RETRIEVAL_V2_CANDIDATE_SENTENCES_PER_DOC", 8)))
        self.retrieval_v2_max_selected_docs = max(4, min(20, self._safe_env_int("RETRIEVAL_V2_MAX_SELECTED_DOCS", 12)))
        self.retrieval_v2_passages_per_doc = max(2, min(8, self._safe_env_int("RETRIEVAL_V2_PASSAGES_PER_DOC", 4)))
        self.retrieval_v2_max_selected_passages = max(8, min(40, self._safe_env_int("RETRIEVAL_V2_MAX_SELECTED_PASSAGES", 20)))

    @staticmethod
    def _safe_env_int(name, default):
        try:
            return int(str(os.getenv(name, str(default))).strip())
        except Exception:
            return default

    @staticmethod
    def _normalize_source_modality(source_modality):
        value = str(source_modality or "text").strip().lower()
        if value in {"image", "img"}:
            return "image"
        if value in {"pdf", "document"}:
            return "pdf"
        if value in {"web", "url"}:
            return "web"
        return "text"

    def _scoring_profile_for_modality(self, source_modality):
        modality = self._normalize_source_modality(source_modality)
        profiles = {
            "text": {
                "strong_relevance": self.strong_relevance_threshold,
                "strong_quality": self.strong_quality_threshold,
                "soft_relevance": self.soft_relevance_threshold,
                "soft_quality": self.soft_quality_threshold,
                "min_strong_evidence": self.min_strong_evidence_for_forced_verdict,
                "single_source_decisive_confidence": self.single_source_decisive_confidence,
                "single_source_min_weight": self.single_source_min_weight,
            },
            "web": {
                "strong_relevance": self.strong_relevance_threshold,
                "strong_quality": self.strong_quality_threshold,
                "soft_relevance": self.soft_relevance_threshold,
                "soft_quality": self.soft_quality_threshold,
                "min_strong_evidence": self.min_strong_evidence_for_forced_verdict,
                "single_source_decisive_confidence": self.single_source_decisive_confidence,
                "single_source_min_weight": self.single_source_min_weight,
            },
            "pdf": {
                "strong_relevance": 0.48,
                "strong_quality": 0.45,
                "soft_relevance": 0.34,
                "soft_quality": 0.30,
                "min_strong_evidence": 1,
                "single_source_decisive_confidence": 0.89,
                "single_source_min_weight": 0.72,
            },
            "image": {
                "strong_relevance": 0.55,
                "strong_quality": 0.50,
                "soft_relevance": 0.40,
                "soft_quality": 0.34,
                "min_strong_evidence": 2,
                "single_source_decisive_confidence": 0.92,
                "single_source_min_weight": 0.78,
            },
        }
        return modality, profiles[modality]

    def _trim_evidence_payload(self, rows):
        # Deduplicate by normalized text and limit to top 4 by combined_score
        seen = set()
        trimmed = []
        for row in sorted(rows or [], key=lambda x: float(x.get("combined_score", 0.0)), reverse=True):
            text = (row.get("text") or "").strip().lower()
            if not text or text in seen:
                continue
            if len(text.split()) < 6 or len(text.split()) > 80:
                continue
            seen.add(text)
            item = dict(row)
            item.pop("context_text", None)
            trimmed.append(item)
            if len(trimmed) >= 4:
                break
        return trimmed

    @staticmethod
    def _raise_if_cancelled(cancel_event=None):
        if cancel_event is not None and cancel_event.is_set():
            raise asyncio.CancelledError()

    @staticmethod
    def _emit_progress(progress_callback=None, **event):
        if progress_callback is None:
            return
        try:
            progress_callback(event)
        except Exception:
            return

    @staticmethod
    def _dedupe_scored_evidence_by_url(rows, max_per_url=1):
        try:
            max_per_url = max(1, int(max_per_url))
        except Exception:
            max_per_url = 1

        grouped = {}
        for row in rows or []:
            item = dict(row or {})
            url = str(item.get("url") or "").strip().lower()
            if not url:
                continue
            grouped.setdefault(url, []).append(item)

        deduped = []
        for _, items in grouped.items():
            ranked = sorted(
                items,
                key=lambda item: (
                    float(item.get("combined_score") or 0.0),
                    float(item.get("relevance_score") or 0.0),
                    float(item.get("quality_score") or 0.0),
                    float(item.get("weight") or 0.0),
                ),
                reverse=True,
            )
            deduped.extend(ranked[:max_per_url])

        deduped.sort(
            key=lambda item: (
                float(item.get("combined_score") or 0.0),
                float(item.get("relevance_score") or 0.0),
                float(item.get("quality_score") or 0.0),
            ),
            reverse=True,
        )
        return deduped

    @staticmethod
    async def _flush_progress():
        await asyncio.sleep(0)

    def _finalize_api_payload(self, payload):
        result = dict(payload or {})
        result["evidence"] = self._trim_evidence_payload(result.get("evidence", []))

        if not self.include_verbose_api_fields:
            result.pop("transparency", None)
            result.pop("search_queries", None)
            result.pop("ux_warnings", None)

        return result

    @staticmethod
    def _extract_domain(url):
        try:
            parsed = urlparse(str(url or ""))
            domain = parsed.netloc.lower()
            if domain.startswith("www."):
                domain = domain[4:]
            return domain
        except Exception:
            return ""

    @staticmethod
    def _domain_matches(domain, allowed_domain):
        domain = str(domain or "").lower().strip()
        allowed_domain = str(allowed_domain or "").lower().strip()
        if not domain or not allowed_domain:
            return False
        return domain == allowed_domain or domain.endswith(f".{allowed_domain}")

    def _is_indian_multilingual_claim(self, language, context_result=None):
        return False

    def _is_india_scoped_source(self, row, context_result=None):
        return False

    def _filter_national_source_evidence(self, evidence_rows, context_result=None):
        context_result = context_result or {}
        india_scoped = [
            row for row in (evidence_rows or [])
            if self._is_india_scoped_source(row, context_result=context_result)
        ]
        return india_scoped

    def _get_session_cache_short_circuit_hits(self, claim, context_result=None, source_url=None, source_text=None, trace=None):
        if not self.enable_session_cache_short_circuit:
            return []
        if source_url is not None or not source_text:
            return []

        cache_hits, cache_lookup_stats = self._session_retrieval_cache.lookup(
            claim,
            context_result=context_result,
            max_items=3,
        )
        if isinstance(trace, dict):
            trace["session_cache_lookup"] = cache_lookup_stats

        if not cache_hits:
            return []

        best_similarity = max(float(item.get("session_cache_similarity", 0.0) or 0.0) for item in cache_hits)
        if best_similarity < self.session_cache_short_circuit_min_similarity:
            return []

        if isinstance(trace, dict):
            trace["session_cache_short_circuit"] = {
                "enabled": True,
                "best_similarity": round(best_similarity, 3),
                "returned_items": len(cache_hits),
            }
        return [dict(item) for item in cache_hits]

    @staticmethod
    def _source_text_cache_key(source_text):
        normalized = " ".join((source_text or "").split()).strip().lower()
        if len(normalized) < 120:
            return None
        return hashlib.sha1(normalized.encode("utf-8", errors="ignore")).hexdigest()

    def _get_document_source_cache_hits(self, source_url=None, source_text=None, trace=None):
        if source_url is not None or not source_text:
            return []
        cache_key = self._source_text_cache_key(source_text)
        if not cache_key:
            return []
        cached = self._document_source_evidence_cache.get(cache_key) or []
        if isinstance(trace, dict):
            trace["document_source_cache_lookup"] = {
                "cache_key": cache_key[:12],
                "hit": bool(cached),
                "returned_items": len(cached),
            }
        return [dict(item) for item in cached]

    def _store_document_source_cache(self, source_url=None, source_text=None, evidence_rows=None, trace=None):
        if source_url is not None or not source_text:
            return
        cache_key = self._source_text_cache_key(source_text)
        if not cache_key:
            return
        cached_rows = []
        for ev in evidence_rows or []:
            text = (ev.get("text") or "").strip()
            if len(text.split()) < 20:
                continue
            cached_rows.append(dict(ev))
            if len(cached_rows) >= 8:
                break
        if not cached_rows:
            return
        self._document_source_evidence_cache[cache_key] = cached_rows
        if isinstance(trace, dict):
            trace["document_source_cache_store"] = {
                "cache_key": cache_key[:12],
                "stored_items": len(cached_rows),
            }

    @staticmethod
    def _consolidate_document_results(results, trace=None):
        grouped = {}
        for item in results:
            key = item.get("url") or item.get("source")
            grouped.setdefault(key, []).append(item)

        consolidated = []
        trace_rows = []
        for key, items in grouped.items():
            ranked_items = sorted(
                items,
                key=lambda item: (
                    float(item.get("combined_score") or 0.0),
                    float(item.get("confidence") or 0.0),
                    float(item.get("weight") or 0.0),
                ),
                reverse=True,
            )
            support_items = [item for item in ranked_items if item.get("stance") == "SUPPORT"]
            refute_items = [item for item in ranked_items if item.get("stance") == "REFUTE"]
            neutral_items = [item for item in ranked_items if item.get("stance") == "NEUTRAL"]
            dominant_items = support_items if len(support_items) >= len(refute_items) else refute_items

            if dominant_items:
                best = max(
                    dominant_items,
                    key=lambda item: float(item.get("confidence", 0.0)) * float(item.get("weight", 0.0)),
                )
                merged = dict(best)
                consensus_boost = min(0.1, 0.03 * max(len(dominant_items) - 1, 0))
                merged["confidence"] = round(
                    min(
                        1.0,
                        (
                            sum(float(item.get("confidence", 0.0)) for item in dominant_items)
                            / max(len(dominant_items), 1)
                        ) + consensus_boost,
                    ),
                    3,
                )
                merged["weight"] = round(
                    min(
                        1.0,
                        max(float(item.get("weight", 0.0)) for item in dominant_items) + consensus_boost,
                    ),
                    3,
                )
            else:
                best = ranked_items[0]
                merged = dict(best)

            retained_passages = []
            for item in ranked_items[:3]:
                retained_passages.append({
                    "text": item.get("text"),
                    "stance": item.get("stance"),
                    "confidence": round(float(item.get("confidence", 0.0)), 3),
                    "weight": round(float(item.get("weight", 0.0)), 3),
                    "relevance_score": round(float(item.get("relevance_score", 0.0)), 3),
                    "quality_score": round(float(item.get("quality_score", 0.0)), 3),
                    "combined_score": round(float(item.get("combined_score", 0.0)), 4),
                    "evidence_tier": item.get("evidence_tier", "soft"),
                })

            merged["passage_count"] = len(ranked_items)
            merged["support_passages"] = len(support_items)
            merged["refute_passages"] = len(refute_items)
            merged["neutral_passages"] = len(neutral_items)
            merged["document_score"] = round(max(float(item.get("combined_score") or 0.0) for item in ranked_items), 4)
            merged["document_has_conflict"] = bool(support_items and refute_items)
            merged["retained_passages"] = retained_passages
            merged["context_text"] = "\n".join(
                passage["text"] for passage in retained_passages[:2] if passage.get("text")
            )[:800]
            consolidated.append(merged)

            trace_rows.append({
                "document_key": key,
                "source": merged.get("source"),
                "url": merged.get("url"),
                "passage_count": len(ranked_items),
                "support_passages": len(support_items),
                "refute_passages": len(refute_items),
                "neutral_passages": len(neutral_items),
                "document_score": merged["document_score"],
                "selected_stance": merged.get("stance"),
                "selected_text": merged.get("text"),
                "retained_passages": retained_passages,
            })

        if isinstance(trace, dict):
            trace["document_consolidation"] = trace_rows

        return consolidated

    @property
    def relevance_scorer(self):
        if self._relevance_scorer is None:
            self._relevance_scorer = RelevanceScorer()
        return self._relevance_scorer

    @property
    def stance(self):
        if self._stance is None:
            self._stance = StanceDetector(v2_mode=self.enable_retrieval_v2)
        return self._stance

    @property
    def verifier_v2(self):
        if self._verifier_v2 is None:
            self._verifier_v2 = VerifierV2(self.stance)
        return self._verifier_v2

    @property
    def llm_verifier(self):
        if self._llm_verifier is None:
            self._llm_verifier = LLMVerifier()
        return self._llm_verifier

    @property
    def index_reranker(self):
        if self._index_reranker is None:
            self._index_reranker = IndexReranker()
        return self._index_reranker

    @property
    def retrieval_v2(self):
        if self._retrieval_v2 is None:
            from pipeline.retrieval_v2 import RetrievalPipelineV2
            self._retrieval_v2 = RetrievalPipelineV2(
                relevance_scorer=self.relevance_scorer,
                quality_scorer=self.quality_scorer,
                candidate_sentences_per_doc=self.retrieval_v2_candidate_sentences_per_doc,
                max_selected_docs=self.retrieval_v2_max_selected_docs,
                passages_per_doc=self.retrieval_v2_passages_per_doc,
                max_selected_passages=self.retrieval_v2_max_selected_passages,
            )
        return self._retrieval_v2

    def _build_transparency(
        self,
        claim_type_result,
        context_result,
        language,
        source_modality,
        scoring_profile,
        evidence_retrieved,
        evidence_cleaned,
        scored_evidence,
        results,
        strong_evidence_count,
        forced_neutral,
        logic_engine_injected,
        fallback_evidence_preview=None,
        trace=None,
        stage_timings=None,
        llm_verifier_enabled=None,
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
            "version": "phase6-v2" if self.enable_retrieval_v2 else "phase6-v1",
            "verifier": {
                "verifier_v2_enabled": self.enable_verifier_v2,
                "llm_verifier_enabled": bool(llm_verifier_enabled) and self.llm_verifier.available,
                "llm_verifier_model": self.llm_verifier.model if bool(llm_verifier_enabled) and self.llm_verifier.available else None,
                "llm_verifier_policy": self.llm_verifier.policy if bool(llm_verifier_enabled) else None,
            },
            "language_detected": language,
            "source_modality": source_modality,
            "claim_type": {
                "label": claim_type_result["type"].value,
                "confidence": round(float(claim_type_result.get("confidence", 0.0)), 3),
                "decision_source": claim_type_result.get("decision_source", "unknown"),
            },
            "claim_context": {
                "domain": context_result.get("domain", "general_factual"),
                "subcategory": context_result.get("subcategory", "encyclopedic"),
                "confidence": round(float(context_result.get("confidence", 0.0)), 3),
                "decision_source": context_result.get("decision_source", "unknown"),
                "risk_flags": list(context_result.get("risk_flags", [])),
                "state_focus": context_result.get("state_focus"),
                "local_source_hints": {},
                "taxonomy_version": context_result.get("taxonomy_version", "v1"),
            },
            "routing": {
                "search_queries": list(trace.get("search_queries", [])) if isinstance(trace, dict) else [],
                "search_provider_chain": list(trace.get("search_provider_chain", [])) if isinstance(trace, dict) else [],
                "search_cache_hit": bool(trace.get("search_cache_hit", False)) if isinstance(trace, dict) else False,
                "playwright_used": bool(trace.get("playwright_used", False)) if isinstance(trace, dict) else False,
                "local_rag_hits": list(trace.get("local_rag_hits", [])) if isinstance(trace, dict) else [],
                "session_cache_hits": list(trace.get("session_cache_hits", [])) if isinstance(trace, dict) else [],
                "session_cache_lookup": dict(trace.get("session_cache_lookup", {})) if isinstance(trace, dict) else {},
                "session_cache_store": dict(trace.get("session_cache_store", {})) if isinstance(trace, dict) else {},
                "search_cap": int(trace.get("search_cap", 0)) if isinstance(trace, dict) else 0,
                "retrieval_attempt": int(trace.get("retrieval_attempt", 1)) if isinstance(trace, dict) else 1,
                "retrieval_expanded": bool(trace.get("retrieval_expanded", False)) if isinstance(trace, dict) else False,
            },
            "retrieval_audit": {
                "search_results": list(trace.get("search_results", [])) if isinstance(trace, dict) else [],
                "scraped_pages": list(trace.get("scraped_pages", [])) if isinstance(trace, dict) else [],
                "evidence_selected": list(trace.get("evidence_selected", [])) if isinstance(trace, dict) else [],
            },
            "experimental_rerank": {
                "enabled": bool(trace.get("index_rerank", {}).get("enabled")) if isinstance(trace, dict) else False,
                "baseline_order": list(trace.get("index_rerank_baseline_order", [])) if isinstance(trace, dict) else [],
                "final_order": list(trace.get("index_rerank_final_order", [])) if isinstance(trace, dict) else [],
                "profile": dict(trace.get("index_rerank", {})) if isinstance(trace, dict) else {},
            },
            "retrieval_version": "v2" if self.enable_retrieval_v2 else "v1",
            "reranker_provider": getattr(self.relevance_scorer, "provider_name", "current"),
            "thresholds": {
                "strong_relevance": scoring_profile["strong_relevance"],
                "strong_quality": scoring_profile["strong_quality"],
                "soft_relevance": scoring_profile["soft_relevance"],
                "soft_quality": scoring_profile["soft_quality"],
                "min_strong_evidence_for_definitive_verdict": scoring_profile["min_strong_evidence"],
                "single_source_decisive_confidence": scoring_profile["single_source_decisive_confidence"],
                "single_source_min_weight": scoring_profile["single_source_min_weight"],
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
                "document_level_items": len(results),
                "documents_with_multiple_passages": sum(1 for item in results if int(item.get("passage_count", 1)) > 1),
            },
            "document_consolidation": list(trace.get("document_consolidation", [])) if isinstance(trace, dict) else [],
            "stance_sources": stance_source_counts,
            "policy_flags": {
                "forced_neutral_due_to_weak_evidence": forced_neutral,
                "logic_engine_injected": logic_engine_injected,
            },
            "stage_timings_seconds": dict(stage_timings or {}),
            "fallback_evidence_preview": list(fallback_evidence_preview or []),
        }

    def _build_fallback_evidence_preview(self, evidence_rows, limit=5):
        preview = []
        for ev in evidence_rows[:limit]:
            preview_text = _sanitize_evidence_text(ev.get("text", ""))
            preview.append({
                "source": ev.get("source", "Unknown"),
                "url": ev.get("url"),
                "text": preview_text,
                "weight": round(float(ev.get("weight", 0.0)), 3),
                "confidence": 0.0,
                "stance": "UNSCORED",
                "stance_source": "retrieved_preview",
            })
        return preview

    def _compute_neutral_confidence(self, results=None, scored_evidence=None, forced_neutral=False):
        result_rows = [dict(r) for r in (results or []) if isinstance(r, dict)]
        score_rows = [dict(r) for r in (scored_evidence or []) if isinstance(r, dict)]

        rows = result_rows or score_rows
        if not rows:
            return 0.0

        def _safe_float(row, key, fallback=0.0):
            try:
                return float(row.get(key, fallback) or fallback)
            except Exception:
                return float(fallback)

        source_count = len(rows)
        avg_weight = sum(_safe_float(r, "weight", 0.35) for r in rows) / max(source_count, 1)
        avg_quality = sum(_safe_float(r, "quality_score", 0.35) for r in rows) / max(source_count, 1)
        avg_relevance = sum(_safe_float(r, "relevance_score", 0.30) for r in rows) / max(source_count, 1)

        combined_values = []
        for row in rows:
            combined = _safe_float(row, "combined_score", 0.0)
            if combined <= 0.0:
                combined = _safe_float(row, "relevance_score", 0.30) * _safe_float(row, "quality_score", 0.35)
            combined_values.append(combined)
        avg_combined = sum(combined_values) / max(len(combined_values), 1)

        stance_rows = [r for r in result_rows if str(r.get("stance", "")).upper() in {"SUPPORT", "REFUTE", "NEUTRAL"}]
        support_count = len([r for r in stance_rows if str(r.get("stance", "")).upper() == "SUPPORT"])
        refute_count = len([r for r in stance_rows if str(r.get("stance", "")).upper() == "REFUTE"])
        conflict_penalty = 0.16 if support_count > 0 and refute_count > 0 else 0.0

        confidence = (
            0.10
            + (0.45 * avg_combined)
            + (0.16 * avg_quality)
            + (0.12 * avg_relevance)
            + (0.12 * avg_weight)
            + (0.10 * min(source_count / 10.0, 1.0))
            - conflict_penalty
        )

        upper = 0.58 if forced_neutral else 0.66
        return round(max(0.08, min(upper, confidence)), 3)

    async def run(self, claim, source_url=None, source_text=None, source_language=None, source_modality="text", allow_llm_verifier=None, cancel_event=None, progress_callback=None, search_cap=None, _expanded_retry_done=False, force_fresh_retrieval=False):
        print("\n[Pipeline Analysis Start]")
        self._raise_if_cancelled(cancel_event)
        if search_cap is None:
            search_cap = self.default_search_cap
        try:
            search_cap = int(search_cap)
        except Exception:
            search_cap = self.default_search_cap
        search_cap = max(2, min(self.max_search_cap, search_cap))

        original_claim = claim
        normalized_modality, scoring_profile = self._scoring_profile_for_modality(source_modality)
        self._emit_progress(progress_callback, stage="input", status="done", detail="Claim accepted for analysis")
        await self._flush_progress()
        ux_warnings = _build_ux_warnings(claim)
        llm_verifier_enabled = self.enable_llm_verifier if allow_llm_verifier is None else bool(allow_llm_verifier)
        if normalized_modality == "image":
            llm_verifier_enabled = False
        verifier_v2_enabled = self.enable_verifier_v2 and normalized_modality != "image"

        # trace object for debugging pipeline flow
        trace = {
            "claim": claim,
            "original_claim": original_claim,
            "source_modality": normalized_modality,
            "search_results": [],
            "scraped_pages": [],
            "evidence_selected": [],
            "stance_predictions": [],
            "document_consolidation": [],
            "session_cache_hits": [],
            "session_cache_lookup": {},
            "session_cache_store": {},
            "search_cap": search_cap,
            "retrieval_attempt": 2 if _expanded_retry_done else 1,
            "retrieval_expanded": bool(_expanded_retry_done),
            "final_verdict": None
        }

        total_start = time.time()
        stage_timings = {
            "logical_analysis": 0.0,
            "language_normalization": 0.0,
            "claim_type_classification": 0.0,
            "claim_context_classification": 0.0,
            "evidence_retrieval": 0.0,
            "relevance_quality_total": 0.0,
            "relevance_model_inference": 0.0,
            "quality_scoring": 0.0,
            "stance_total": 0.0,
            "stance_model_inference": 0.0,
            "llm_verifier": 0.0,
            "aggregation": 0.0,
            "total_pipeline": 0.0,
        }

        print("\n==============================")
        print("Processing claim:", _safe_console_text(claim))

        # run logical claim analysis
        start = time.time()
        logic_metadata = self.logical_analyzer.analyze(claim)
        stage_timings["logical_analysis"] = round(time.time() - start, 3)
        print("Logical analyzer:", stage_timings["logical_analysis"], "sec")

        # detect language and normalize claim
        start = time.time()
        self._emit_progress(progress_callback, stage="language", status="active", detail="Detecting language and normalizing claim")
        await self._flush_progress()
        language = source_language or detect_language(claim)
        claim = translate_to_english(claim, language)
        claim = normalize_claim(claim)
        stage_timings["language_normalization"] = round(time.time() - start, 3)
        print("Language + normalization:", stage_timings["language_normalization"], "sec")
        language_detail = f"Language resolved as {language}"
        if str(language).lower() != "en":
            language_detail += "; adapting retrieval to multilingual evidence"
        self._emit_progress(progress_callback, stage="language", status="done", detail=language_detail)
        await self._flush_progress()

        # checkability first
        checkability = self.claim_checkability.classify(
            claim,
            logical_metadata=logic_metadata,
        )
        trace["claim_checkability"] = {
            **checkability,
            "label": getattr(checkability.get("label"), "value", checkability.get("label")),
            "subtype": getattr(checkability.get("subtype"), "value", checkability.get("subtype")),
        }
        if not checkability.get("allowed", True):
            warning = {
                "code": checkability.get("code", "not_checkable"),
                "severity": "error",
                "block": True,
                "message": checkability.get("message", "This input is not a fact-checkable claim."),
            }
            combined_warnings = [warning] + list(ux_warnings or [])
            transparency = {
                "version": "phase6-v1",
                "language_detected": language,
                "status": "blocked_not_checkable",
                "claim_checkability": {
                    **trace["claim_checkability"],
                },
                "stage_timings_seconds": dict(stage_timings),
            }
            return {
                "claim": claim,
                "language": language,
                "evidence": [],
                "final_verdict": "NEUTRAL",
                "confidence": 0.0,
                "conflict_analysis": "Input is not a fact-checkable claim",
                "citations": [],
                "logical_analysis": logic_metadata,
                "explanation": checkability.get("message", "This input is not a fact-checkable claim."),
                "transparency": transparency,
                "search_queries": [],
                "ux_warnings": combined_warnings,
            }

        # classify claim type (FACTUAL, OPINION, NUMERICAL, MIXED)
        start = time.time()
        claim_type_result = self.claim_type_classifier.classify(claim)
        trace["claim_type"] = {
            **claim_type_result,
            "type": claim_type_result["type"].value,
        }
        print(f"Claim type: {claim_type_result['type'].value} (confidence: {claim_type_result['confidence']:.2f})")
        stage_timings["claim_type_classification"] = round(time.time() - start, 3)
        print("Claim type classification:", stage_timings["claim_type_classification"], "sec")

        start = time.time()
        context_result = self.claim_context_classifier.classify(
            claim,
            original_claim=original_claim,
            language=language,
        )
        trace["claim_context"] = dict(context_result)
        print(
            f"Claim context: {context_result['domain']}/{context_result['subcategory']} "
            f"(confidence: {context_result['confidence']:.2f})"
        )
        stage_timings["claim_context_classification"] = round(time.time() - start, 3)
        print("Claim context classification:", stage_timings["claim_context_classification"], "sec")

        # extract domain to exclude original source
        exclude_domain = None
        if source_url:
            exclude_domain = source_url.split("/")[2].replace("www.", "")

        normalized_source_text = source_text
        if source_text:
            normalized_source_text = translate_to_english(source_text, language)
            normalized_source_text = normalize_claim(normalized_source_text)

        cached_evidence_raw = []
        if not _expanded_retry_done and not force_fresh_retrieval:
            cached_evidence_raw = self._get_document_source_cache_hits(
                source_url=source_url,
                source_text=normalized_source_text,
                trace=trace,
            )
            if not cached_evidence_raw:
                cached_evidence_raw = self._get_session_cache_short_circuit_hits(
                claim,
                context_result=context_result,
                source_url=source_url,
                source_text=normalized_source_text,
                trace=trace,
                )

        self._raise_if_cancelled(cancel_event)
        # retrieve evidence from router
        start = time.time()
        if cached_evidence_raw:
            evidence_raw = cached_evidence_raw
            if trace.get("document_source_cache_lookup", {}).get("hit"):
                trace["document_source_cache_hit"] = True
                print("Evidence retrieved from document source cache:", len(evidence_raw))
            else:
                trace["session_cache_hit"] = True
                print("Evidence retrieved from session cache:", len(evidence_raw))
        else:
            try:
                retrieval_source_cap = search_cap
                if normalized_modality == "image":
                    retrieval_source_cap = min(self.max_search_cap, max(search_cap + 2, search_cap))

                # --- Always call crawl4ai for PDF claims (additive) ---
                evidence_raw = []
                crawl4ai_rows = []
                if self.enable_crawl4ai and normalized_modality == "pdf":
                    try:
                        print("[PDF] [Crawl4AI] Crawling evidence for claim...")
                        crawl4ai_rows = await asyncio.get_event_loop().run_in_executor(
                            None,
                            lambda: crawl_claim_evidence(
                                claim,
                                exclude_domain=exclude_domain,
                                language=language,
                                context=context_result,
                                max_results=retrieval_source_cap,
                            )
                        )
                        if crawl4ai_rows:
                            print(f"[PDF] [Crawl4AI] Retrieved {len(crawl4ai_rows)} evidence items.")
                            trace["crawl4ai_used"] = True
                    except Exception as e:
                        print(f"[PDF] [Crawl4AI] Error: {e}")
                        crawl4ai_rows = []

                # Always call router.get_evidence and merge results
                router_rows = await self.router.get_evidence(
                    claim,
                    exclude_domain=exclude_domain,
                    trace=trace,
                    context_result=context_result,
                    claim_type_result=trace["claim_type"],
                    original_claim=original_claim,
                    language=language,
                    source_text=normalized_source_text,
                    progress_callback=progress_callback,
                    max_sources=retrieval_source_cap,
                    force_refresh=bool(_expanded_retry_done or force_fresh_retrieval),
                    source_modality=normalized_modality,
                )
                # Merge crawl4ai and router results, dedupe by URL
                seen_urls = set()
                for row in (crawl4ai_rows or []):
                    url = (row.get("url") or "").strip()
                    if url and url not in seen_urls:
                        evidence_raw.append(row)
                        seen_urls.add(url)
                for row in (router_rows or []):
                    url = (row.get("url") or "").strip()
                    if url and url not in seen_urls:
                        evidence_raw.append(row)
                        seen_urls.add(url)
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
                        "stage_timings_seconds": dict(stage_timings),
                    },
                    "ux_warnings": ux_warnings,
                }

        evidence_retrieved_count = len(evidence_raw)
        self._raise_if_cancelled(cancel_event)

        # store search results in trace
        for ev in evidence_raw:
            trace["search_results"].append({
                "source": ev.get("source"),
                "url": ev.get("url")
            })

        stage_timings["evidence_retrieval"] = round(time.time() - start, 3)
        print("Evidence retrieved:", len(evidence_raw))
        print("Evidence retrieval:", stage_timings["evidence_retrieval"], "sec")

        if not cached_evidence_raw:
            self._store_document_source_cache(
                source_url=source_url,
                source_text=normalized_source_text,
                evidence_rows=evidence_raw,
                trace=trace,
            )

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

        evidence_raw = _sanitize_evidence_rows(evidence_raw)

        print("Cleaned evidence:", len(evidence_raw))
        evidence_cleaned_count = len(evidence_raw)

        self._raise_if_cancelled(cancel_event)
        # compute relevance and quality scores
        start = time.time()
        self._emit_progress(progress_callback, stage="relevance", status="active", detail="Ranking evidence by relevance and quality")
        await self._flush_progress()

        scored_evidence = []
        strong_evidence_count = 0

        if self.enable_retrieval_v2:
            scored_evidence = self.retrieval_v2.select_evidence(
                claim,
                evidence_raw,
                self._sentence_cache,
                context_result=context_result,
                trace=trace,
            )
            strong_evidence_count = sum(
                1 for item in scored_evidence if item.get("evidence_tier") == "strong"
            )

        for ev in ([] if self.enable_retrieval_v2 else evidence_raw):
            self._raise_if_cancelled(cancel_event)

            print("\nChecking source:", ev["source"])
            print("URL:", ev["url"])

            # skip low credibility sources
            if ev["weight"] < 0.2:
                print("Rejected (low credibility)")
                continue

            if ev.get("url") and "/search/" in ev["url"].lower() and ev["weight"] < 0.8:
                print("Rejected (search-shell source)")
                continue

            text = ev.get("text")
            if not text:
                continue

            # extract best sentence from document
            sentence_cache_key = (
                " ".join((claim or "").strip().lower().split()),
                ev.get("url", ""),
                hash(text),
            )
            best_sentences = self._sentence_cache.get(sentence_cache_key)
            if best_sentences is None:
                best_sentences = extract_best_sentences(
                    claim,
                    text,
                    self.relevance_scorer,
                    source_name=ev.get("source"),
                    context_result=context_result,
                )
                self._sentence_cache[sentence_cache_key] = best_sentences

            if not best_sentences:
                continue

            for index, candidate in enumerate(best_sentences):
                best_sentence = candidate["text"]
                selector_score = float(candidate.get("selector_score", 0.0))
                reporting_penalty = float(candidate.get("reporting_penalty", 0.0))
                metadata_penalty = float(candidate.get("metadata_penalty", 0.0))
                direct_answer_bonus = float(candidate.get("direct_answer_bonus", 0.0))
                lead_bonus = float(candidate.get("lead_bonus", 0.0))
                relevance_start = time.time()
                relevance_score = self.relevance_scorer.score(claim, best_sentence)
                stage_timings["relevance_model_inference"] += time.time() - relevance_start
                quality_start = time.time()
                quality_score = self.quality_scorer.score(best_sentence)
                stage_timings["quality_scoring"] += time.time() - quality_start
                effective_relevance = round(min(1.0, (relevance_score * 0.85) + (selector_score * 0.15)), 3)
                overlap_ratio = _claim_evidence_overlap_ratio(claim, best_sentence)

                print("Relevance:", relevance_score)
                print("Selector:", selector_score)
                print("Effective relevance:", effective_relevance)
                print("Quality:", quality_score)
                print("Overlap ratio:", round(overlap_ratio, 3))

                evidence_tier = None
                adjusted_weight = ev["weight"]

                if overlap_ratio < 0.22 and effective_relevance < max(scoring_profile["soft_relevance"], 0.35):
                    print("Rejected evidence (low overlap)")
                    continue

                if (
                    effective_relevance >= scoring_profile["strong_relevance"]
                    and quality_score >= scoring_profile["strong_quality"]
                ):
                    evidence_tier = "strong"
                    strong_evidence_count += 1
                elif (
                    effective_relevance >= scoring_profile["soft_relevance"]
                    and quality_score >= scoring_profile["soft_quality"]
                ):
                    evidence_tier = "soft"
                    adjusted_weight = round(ev["weight"] * (0.8 if index == 0 else 0.72), 3)
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
                    "relevance_score": effective_relevance,
                    "base_relevance_score": relevance_score,
                    "selector_score": selector_score,
                    "reporting_penalty": reporting_penalty,
                    "metadata_penalty": metadata_penalty,
                    "direct_answer_bonus": direct_answer_bonus,
                    "lead_bonus": lead_bonus,
                    "overlap_ratio": round(overlap_ratio, 3),
                    "quality_score": quality_score,
                    "combined_score": round(effective_relevance * quality_score, 4),
                    "evidence_tier": evidence_tier,
                })

                trace["evidence_selected"].append({
                    "url": ev["url"],
                    "sentence": best_sentence,
                    "relevance": effective_relevance,
                    "base_relevance": relevance_score,
                    "selector_score": selector_score,
                    "reporting_penalty": reporting_penalty,
                    "metadata_penalty": metadata_penalty,
                    "direct_answer_bonus": direct_answer_bonus,
                    "lead_bonus": lead_bonus,
                    "overlap_ratio": round(overlap_ratio, 3),
                    "quality": quality_score
                })

        session_cache_hits, cache_lookup_stats = self._session_retrieval_cache.lookup(
            claim,
            context_result=context_result,
            max_items=2,
        )
        trace["session_cache_lookup"] = cache_lookup_stats
        if session_cache_hits:
            existing = {
                ((item.get("url") or "").strip(), " ".join((item.get("text") or "").split()))
                for item in scored_evidence
            }
            appended = []
            duplicates_skipped = 0
            for item in session_cache_hits:
                dedupe_key = ((item.get("url") or "").strip(), " ".join((item.get("text") or "").split()))
                if dedupe_key in existing:
                    duplicates_skipped += 1
                    continue
                existing.add(dedupe_key)
                scored_evidence.append(dict(item))
                appended.append({
                    "source": item.get("source"),
                    "url": item.get("url"),
                    "similarity": item.get("session_cache_similarity"),
                    "from_claim": item.get("session_cache_from_claim"),
                })
            trace["session_cache_hits"] = appended
            trace["session_cache_lookup"]["appended_items"] = len(appended)
            trace["session_cache_lookup"]["duplicates_skipped"] = duplicates_skipped

        # abstain early if no evidence passes filtering
        if not scored_evidence:
            print("No usable evidence found - abstaining")
            fallback_evidence_preview = self._build_fallback_evidence_preview(evidence_raw)
            abstain_confidence = self._compute_neutral_confidence(
                results=[],
                scored_evidence=fallback_evidence_preview,
                forced_neutral=True,
            )
            return self._finalize_api_payload({
                "claim": claim,
                "language": language,
                "evidence": fallback_evidence_preview,
                "final_verdict": "NEUTRAL",
                "confidence": abstain_confidence,
                "conflict_analysis": "Insufficient evidence",
                "citations": [],
                "logical_analysis": logic_metadata,
                "explanation": "No sufficiently relevant and high-quality evidence was found.",
                "transparency": self._build_transparency(
                    claim_type_result=claim_type_result,
                    context_result=context_result,
                    language=language,
                    source_modality=normalized_modality,
                    scoring_profile=scoring_profile,
                    evidence_retrieved=evidence_retrieved_count,
                    evidence_cleaned=evidence_cleaned_count,
                    scored_evidence=[],
                    results=[],
                    strong_evidence_count=0,
                    forced_neutral=True,
                    logic_engine_injected=False,
                    fallback_evidence_preview=fallback_evidence_preview,
                    trace=trace,
                    stage_timings=stage_timings,
                    llm_verifier_enabled=llm_verifier_enabled,
                ),
                "search_queries": list(trace.get("search_queries", [])),
                "ux_warnings": ux_warnings,
            })

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

        # Avoid duplicate source rows from the same URL in final evidence output.
        scored_evidence = self._dedupe_scored_evidence_by_url(scored_evidence, max_per_url=1)

        scored_evidence = scored_evidence[:search_cap]

        trace["session_cache_store"] = self._session_retrieval_cache.store(
            claim,
            context_result=context_result,
            evidence_rows=scored_evidence,
        )

        stage_timings["relevance_quality_total"] = round(time.time() - start, 3)
        stage_timings["relevance_model_inference"] = round(stage_timings["relevance_model_inference"], 3)
        stage_timings["quality_scoring"] = round(stage_timings["quality_scoring"], 3)
        print("Relevance + quality:", stage_timings["relevance_quality_total"], "sec")
        self._emit_progress(progress_callback, stage="relevance", status="done", detail=f"Ranked {len(scored_evidence)} evidence item(s)")
        await self._flush_progress()

        self._raise_if_cancelled(cancel_event)
        # run stance detection
        start = time.time()
        self._emit_progress(progress_callback, stage="stance", status="active", detail="Running stance analysis on shortlisted evidence")
        await self._flush_progress()

        results = []
        stance_results = None
        if not verifier_v2_enabled:
            # Use context window for stance detection if available
            highlighted_texts = [ev.get("context_text") or ev["text"] for ev in scored_evidence]
            stance_results = self.stance.detect_many(highlighted_texts, claim)

        for index, ev in enumerate(scored_evidence):
            self._raise_if_cancelled(cancel_event)

            highlighted = ev["text"]
            highlighted = _sanitize_evidence_text(highlighted)

            print("\nSTANCE CHECK")
            safe_highlighted = (highlighted or "").replace("\ufeff", "").encode(
                sys.stdout.encoding or "utf-8",
                errors="replace",
            ).decode(sys.stdout.encoding or "utf-8", errors="replace")
            print("Evidence:", safe_highlighted)

            verifier_input = ev.get("context_text") if verifier_v2_enabled else None
            if verifier_input is not None:
                verifier_input = _sanitize_evidence_text(verifier_input)
            if verifier_v2_enabled:
                stance_result = self.verifier_v2.verify(claim, highlighted, verifier_input)
            else:
                stance_result = stance_results[index]

            print("Stance:", _safe_console_text(stance_result))

            overlap_ratio = _claim_evidence_overlap_ratio(claim, highlighted)
            llm_overlap_ok = (
                overlap_ratio >= 0.34
                or float(ev.get("selector_score", 0.0) or 0.0) >= 0.88
                or float(ev.get("relevance_score", 0.0) or 0.0) >= 0.9
            )
            if llm_verifier_enabled and llm_overlap_ok and self.llm_verifier.should_verify(len(results), stance_result.get("stance")):
                try:
                    llm_start = time.time()
                    llm_result = self.llm_verifier.verify(claim, highlighted, ev.get("context_text"))
                    stage_timings["llm_verifier"] += time.time() - llm_start
                    regional_local_claim = "regional_local_claim" in set((context_result or {}).get("risk_flags", []))
                    llm_non_neutral_allowed = True
                    if (
                        regional_local_claim
                        and llm_result.get("stance") in {"SUPPORT", "REFUTE"}
                        and not _is_official_public_admin_source(ev.get("url"))
                    ):
                        llm_non_neutral_allowed = False
                        trace.setdefault("llm_verifier_suppressed", []).append({
                            "url": ev.get("url"),
                            "stance": llm_result.get("stance"),
                            "reason": "regional_local_non_official_source",
                        })
                    trusted_llm_source = _is_trusted_llm_override_source(ev.get("url"))
                    llm_override_allowed = (
                        trusted_llm_source
                        and overlap_ratio >= 0.45
                        and float(ev.get("relevance_score", 0.0) or 0.0) >= 0.75
                        and float(ev.get("selector_score", 0.0) or 0.0) >= 0.7
                    )
                    if llm_result.get("stance") != "NEUTRAL" and llm_non_neutral_allowed:
                        if llm_override_allowed:
                            stance_result = llm_result
                        else:
                            trace.setdefault("llm_verifier_suppressed", []).append({
                                "url": ev.get("url"),
                                "stance": llm_result.get("stance"),
                                "reason": "override_guard_low_trust_or_low_overlap",
                                "overlap_ratio": round(overlap_ratio, 3),
                            })
                    elif llm_result.get("stance") == "NEUTRAL" and stance_result.get("stance") == "NEUTRAL":
                        stance_result = llm_result
                except Exception as exc:
                    trace.setdefault("llm_verifier_errors", []).append(str(exc))
            elif llm_verifier_enabled and not llm_overlap_ok and self.llm_verifier.should_verify(len(results), stance_result.get("stance")):
                trace.setdefault("llm_verifier_skipped", []).append({
                    "url": ev.get("url"),
                    "reason": "low_claim_overlap",
                    "overlap_ratio": round(overlap_ratio, 3),
                    "selector_score": round(float(ev.get("selector_score", 0.0) or 0.0), 3),
                    "relevance_score": round(float(ev.get("relevance_score", 0.0) or 0.0), 3),
                })

            if stance_result.get("stance") == "NEUTRAL":
                year_check = year_reasoning(claim, highlighted)
                if year_check:
                    stance_result = {
                        "stance": year_check,
                        "confidence": 0.88,
                        "source": "heuristic_year_rescue",
                    }
                elif not self.enable_retrieval_v2:
                    rank_check = numeric_rank_reasoning(claim, highlighted)
                    if rank_check:
                        stance_result = {
                            "stance": rank_check,
                            "confidence": 0.9 if rank_check == "REFUTE" else 0.86,
                            "source": "heuristic_rank_rescue",
                        }
                # Numeric proximity rescue for continuous values (not years/ranks)
                if stance_result.get("stance") == "NEUTRAL":
                    claim_type = claim_type_label_lower(claim_type_result)
                    domain = str((context_result or {}).get("domain") or "").lower()
                    # Only apply proximity for factual/numerical claims in science/measurement/statistics domains
                    allow_proximity = (
                        claim_type in {"factual", "numerical"}
                        and domain in {"science", "measurement", "statistics", "space_astronomy", "health", "general_factual"}
                    )
                    if allow_proximity:
                        claim_nums = re.findall(r"[\d,]+(?:\.\d+)?", claim)
                        ev_nums = re.findall(r"[\d,]+(?:\.\d+)?", highlighted)
                        claim_vals = collect_non_year_numeric_values(claim_nums)
                        ev_vals = collect_non_year_numeric_values(ev_nums)
                        rel_diff = best_numeric_pairwise_rel_diff(claim_vals, ev_vals)
                        if rel_diff is not None and rel_diff <= 0.02:  # within 2% (pairwise)
                            stance_result = {"stance": "SUPPORT", "confidence": 0.82, "source": "numeric_proximity_rescue"}
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
                "base_relevance_score": ev.get("base_relevance_score"),
                "selector_score": ev.get("selector_score"),
                "context_text": ev.get("context_text"),
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

        if self.enable_index_rerank_experiment:
            trace["index_rerank_baseline_order"] = [
                {
                    "source": item.get("source"),
                    "url": item.get("url"),
                    "stance": item.get("stance"),
                    "combined_score": round(float(item.get("combined_score") or 0.0), 4),
                    "confidence": round(float(item.get("confidence") or 0.0), 3),
                    "text": item.get("text"),
                }
                for item in results
            ]
            results = self.index_reranker.rerank_results(claim, results, trace=trace)
            trace["index_rerank_final_order"] = [
                {
                    "source": item.get("source"),
                    "url": item.get("url"),
                    "stance": item.get("stance"),
                    "combined_score": round(float(item.get("combined_score") or 0.0), 4),
                    "confidence": round(float(item.get("confidence") or 0.0), 3),
                    "rerank_bonus": round(float(item.get("index_rerank_bonus") or 0.0), 4),
                    "text": item.get("text"),
                }
                for item in results
            ]

        results = self._consolidate_document_results(results, trace=trace)
        print("Document-level evidence items:", len(results))
        stage_timings["stance_total"] = round(time.time() - start, 3)
        stage_timings["stance_model_inference"] = round(max(0.0, stage_timings["stance_total"] - stage_timings["llm_verifier"]), 3)
        stage_timings["llm_verifier"] = round(stage_timings["llm_verifier"], 3)
        print("Semantic + NLI:", stage_timings["stance_total"], "sec")
        self._emit_progress(progress_callback, stage="stance", status="done", detail=f"Evaluated stance across {len(results)} evidence item(s)")
        await self._flush_progress()

        # logic engine reasoning pass
        logic_verdict = self.logic_engine.analyze(claim, results)
        non_neutral = [r for r in results if r.get("stance") in {"SUPPORT", "REFUTE"}]
        logic_engine_injected = False
        if (
            logic_verdict in {"SUPPORT", "REFUTE"}
            and len(non_neutral) >= 2
            and strong_evidence_count >= scoring_profile["min_strong_evidence"]
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
        self._emit_progress(progress_callback, stage="verdict", status="active", detail="Aggregating final verdict")
        await self._flush_progress()

        verdict, confidence = aggregate_results(results)
        conflict_summary = self.conflict_analyzer.analyze(results)

        # Abstain when there is no reliable non-neutral signal.
        forced_neutral = False
        non_neutral_count = len([r for r in results if r.get("stance") in {"SUPPORT", "REFUTE"}])
        support_items = [r for r in results if r.get("stance") == "SUPPORT"]
        refute_items = [r for r in results if r.get("stance") == "REFUTE"]
        decisive_single = any(
            r.get("stance") in {"SUPPORT", "REFUTE"}
            and float(r.get("confidence", 0.0)) >= scoring_profile["single_source_decisive_confidence"]
            and float(r.get("weight", 0.0)) >= scoring_profile["single_source_min_weight"]
            for r in results
        )
        dominant_items = support_items if len(support_items) >= len(refute_items) else refute_items
        soft_consensus = False
        soft_directional_consensus = False
        if (
            len(dominant_items) >= self.soft_consensus_min_items
            and (len(support_items) == 0 or len(refute_items) == 0)
        ):
            avg_confidence = sum(float(r.get("confidence", 0.0)) for r in dominant_items) / max(len(dominant_items), 1)
            avg_weight = sum(float(r.get("weight", 0.0)) for r in dominant_items) / max(len(dominant_items), 1)
            if (
                avg_confidence >= self.soft_consensus_min_avg_confidence
                and avg_weight >= self.soft_consensus_min_avg_weight
            ):
                soft_consensus = True
        if (
            len(dominant_items) >= self.soft_directional_min_items
            and (len(support_items) == 0 or len(refute_items) == 0)
        ):
            avg_confidence = sum(float(r.get("confidence", 0.0)) for r in dominant_items) / max(len(dominant_items), 1)
            avg_weight = sum(float(r.get("weight", 0.0)) for r in dominant_items) / max(len(dominant_items), 1)
            total_weight = sum(float(r.get("weight", 0.0)) for r in dominant_items)
            if (
                avg_confidence >= self.soft_directional_min_avg_confidence
                and avg_weight >= self.soft_directional_min_avg_weight
                and total_weight >= self.soft_directional_min_total_weight
            ):
                soft_directional_consensus = True
        if (
            (
                strong_evidence_count < scoring_profile["min_strong_evidence"]
                and not decisive_single
                and not soft_consensus
                and not soft_directional_consensus
            )
            or non_neutral_count == 0
        ):
            verdict = "NEUTRAL"
            confidence = min(confidence, 0.55)
            conflict_summary = "Insufficient decisive evidence for definitive verdict"
            forced_neutral = True

        all_neutral = bool(results) and all(str(r.get("stance", "")).upper() == "NEUTRAL" for r in results)
        if (
            verdict == "NEUTRAL"
            and all_neutral
            and search_cap < self.max_search_cap
            and not _expanded_retry_done
            and self.enable_neutral_expanded_retry
        ):
            print(f"All evidence remained neutral; retrying with expanded source cap to {self.max_search_cap}.")
            return await self.run(
                original_claim,
                source_url=source_url,
                source_text=source_text,
                source_language=source_language,
                source_modality=source_modality,
                allow_llm_verifier=allow_llm_verifier,
                cancel_event=cancel_event,
                progress_callback=progress_callback,
                search_cap=self.max_search_cap,
                _expanded_retry_done=True,
            )

        if verdict == "NEUTRAL":
            confidence = self._compute_neutral_confidence(
                results=results,
                scored_evidence=scored_evidence,
                forced_neutral=forced_neutral,
            )

        decisive_external = [
            row for row in results
            if str(row.get("stance") or "").upper() in {"SUPPORT", "REFUTE"}
            and str(row.get("source") or "").lower() != "logic_engine"
            and not str(row.get("url") or "").startswith("internal://")
        ]
        strong_support_external = [
            row for row in decisive_external
            if str(row.get("stance") or "").upper() == "SUPPORT"
            and float(row.get("confidence", 0.0) or 0.0) >= 0.58
        ]
        strong_refute_external = [
            row for row in decisive_external
            if str(row.get("stance") or "").upper() == "REFUTE"
            and float(row.get("confidence", 0.0) or 0.0) >= 0.58
        ]

        if verdict == "TRUE" and not strong_support_external:
            verdict = "NEUTRAL"
            forced_neutral = True
            conflict_summary = "No decisive external supporting evidence"
            confidence = self._compute_neutral_confidence(
                results=results,
                scored_evidence=scored_evidence,
                forced_neutral=True,
            )
        elif verdict == "FALSE" and not strong_refute_external:
            verdict = "NEUTRAL"
            forced_neutral = True
            conflict_summary = "No decisive external refuting evidence"
            confidence = self._compute_neutral_confidence(
                results=results,
                scored_evidence=scored_evidence,
                forced_neutral=True,
            )

        # Guardrail: mixed support/refute evidence with weak margin should not end as TRUE/FALSE.
        if verdict in {"TRUE", "FALSE"} and support_items and refute_items:
            support_strength = sum(_weighted_direction_strength(r) for r in support_items)
            refute_strength = sum(_weighted_direction_strength(r) for r in refute_items)
            total_strength = support_strength + refute_strength
            strength_margin = abs(support_strength - refute_strength) / max(total_strength, 1e-6)
            trusted_support_max = max(
                (_weighted_direction_strength(r) for r in support_items if _is_trusted_llm_override_source(r.get("url"))),
                default=0.0,
            )
            trusted_refute_max = max(
                (_weighted_direction_strength(r) for r in refute_items if _is_trusted_llm_override_source(r.get("url"))),
                default=0.0,
            )
            dominant_trusted_strength = max(trusted_support_max, trusted_refute_max)
            opposing_strength = min(support_strength, refute_strength)
            allow_dominant_trusted_decision = (
                dominant_trusted_strength >= 0.55
                and opposing_strength <= 0.42
                and strength_margin >= 0.12
            )
            if (confidence < 0.4 or strength_margin < 0.2) and not allow_dominant_trusted_decision:
                verdict = "NEUTRAL"
                forced_neutral = True
                conflict_summary = "Conflicting support/refute evidence with weak decision margin"
                confidence = self._compute_neutral_confidence(
                    results=results,
                    scored_evidence=scored_evidence,
                    forced_neutral=True,
                )

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
            context_result=context_result,
            language=language,
            source_modality=normalized_modality,
            scoring_profile=scoring_profile,
            evidence_retrieved=evidence_retrieved_count,
            evidence_cleaned=evidence_cleaned_count,
            scored_evidence=scored_evidence,
            results=results,
            strong_evidence_count=strong_evidence_count,
            forced_neutral=forced_neutral,
            logic_engine_injected=logic_engine_injected,
            fallback_evidence_preview=[],
            trace=trace,
            stage_timings=stage_timings,
            llm_verifier_enabled=llm_verifier_enabled,
        )

        trace["final_verdict"] = {
            "verdict": verdict,
            "confidence": confidence
        }
        self._emit_progress(progress_callback, stage="verdict", status="done", detail=f"{verdict} at {round(float(confidence or 0.0), 3)} confidence")

        print("\n========== FINAL RESULT ==========")
        print("Verdict:", verdict)
        print("Confidence:", confidence)
        print("Conflict:", conflict_summary)

        stage_timings["aggregation"] = round(time.time() - start, 3)
        stage_timings["total_pipeline"] = round(time.time() - total_start, 3)
        transparency["stage_timings_seconds"] = dict(stage_timings)
        print("Aggregation:", stage_timings["aggregation"], "sec")
        print("TOTAL PIPELINE TIME:", stage_timings["total_pipeline"], "sec")


        with open("pipeline_trace.json", "w", encoding="utf-8") as f:
            json.dump(trace, f, indent=2)

        return self._finalize_api_payload({
            "claim": claim,
            "claim_original": original_claim,
            "language": language,
            "evidence": results,
            "final_verdict": verdict,
            "confidence": confidence,
            "conflict_analysis": conflict_summary,
            "citations": citations,
            "logical_analysis": logic_metadata,
            "explanation": explanation,
            "transparency": transparency,
            "search_queries": list(trace.get("search_queries", [])),
            "ux_warnings": ux_warnings,
        })






