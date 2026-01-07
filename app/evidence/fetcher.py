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
        label, score = detect_stance(claim, e["text"])
        stances.append({
            "label": label,
            "confidence": score,
            "source": e.get("source"),
            "url": e.get("url"),
            "similarity": e.get("similarity")
        })

    verdict = consensus_verdict(stances)

    logger.info(f"VERDICT: {verdict}")
    logger.info("=== FACT CHECK END ===")

    return {
        "claim": claim,
        "verdict": verdict,
        "evidence_used": len(relevant),
        "stances": stances,
        "scraping_metrics": metrics.summary()
    }
