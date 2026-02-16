from typing import Dict, List

from app.utils.logger import logger

from app.evidence.search import search_web
from app.evidence.scraper import scrape_article
from app.evidence.wikidata import fetch_wikipedia_evidence
from app.evidence.gdelt import fetch_gdelt_news
from app.evidence.newsapi import fetch_newsapi

from app.semantic.encoder import encode
from app.semantic.evidence_embedder import embed_evidence
from app.semantic.similarity import filter_by_similarity
from app.semantic.stance import attach_stance
from app.verdict.consensus import consensus_verdict
from app.verdict.confidence import calibrate_confidence
from app.verdict.explanation import build_explanation

from app.evidence.metrics import ScrapeMetrics
from app.evidence.quality import deduplicate


async def fact_check_pipeline(claim: str) -> Dict:
    metrics = ScrapeMetrics()
    raw_evidence: List[dict] = []

    logger.info("=== FACT CHECK START ===")
    logger.info(f"CLAIM: {claim}")

    claim_vec = encode(claim)

    try:
        wiki = await fetch_wikipedia_evidence(claim)
        raw_evidence.extend(wiki or [])
    except Exception as e:
        logger.warning(f"[WIKI ERROR] {e}")

    try:
        raw_evidence.extend(fetch_gdelt_news(claim) or [])
    except Exception as e:
        logger.warning(f"[GDELT ERROR] {e}")

    try:
        raw_evidence.extend(fetch_newsapi(claim) or [])
    except Exception as e:
        logger.warning(f"[NEWSAPI ERROR] {e}")

    urls = search_web(claim)
    logger.info(f"[SEARCH] {len(urls)} URLs")

    for url in urls:
        metrics.start_url()
        try:
            text = scrape_article(url)
            metrics.end_url(success=bool(text))
            if text:
                raw_evidence.append({
                    "source": "web",
                    "url": url,
                    "text": text
                })
        except Exception:
            metrics.end_url(success=False)

    raw_evidence = deduplicate(raw_evidence)

    embedded_evidence = embed_evidence(raw_evidence)

    relevant = filter_by_similarity(
        claim_vec,
        embedded_evidence,
        threshold=0.45
    )

    stances = []
    for e in relevant:
        with_stance = attach_stance(claim, e)
        stances.append({
            "label": with_stance.get("label", "neutral"),
            "confidence": with_stance.get("confidence", 0.0),
            "source": with_stance.get("source"),
            "url": with_stance.get("url"),
            "similarity": with_stance.get("similarity")
        })

    verdict, consensus_score = consensus_verdict(stances)
    confidence = calibrate_confidence(verdict, stances)
    explanation = build_explanation(verdict, stances)

    logger.info(f"VERDICT: {verdict} ({confidence})")
    logger.info("=== FACT CHECK END ===")

    return {
        "claim": claim,
        "verdict": verdict,
        "confidence": confidence,
        "consensus_score": round(consensus_score, 3),
        "explanation": explanation,
        "evidence_used": len(relevant),
        "stances": stances,
        "scraping_metrics": metrics.summary()
    }


async def _single_claim_pipeline(claim: str) -> Dict:
    return await fact_check_pipeline(claim)
