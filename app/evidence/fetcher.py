import aiohttp

from app.evidence.search import search_web
from app.evidence.scraper import scrape_article

WIKI_API = "https://en.wikipedia.org/api/rest_v1/page/summary/"

# ---------- WIKIPEDIA (ASYNC) ----------
async def fetch_wikipedia_evidence_async(claim: str):
    try:
        keyword = " ".join(claim.split()[:5])
        url = WIKI_API + keyword.replace(" ", "%20")

        timeout = aiohttp.ClientTimeout(total=3)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:
                if response.status != 200:
                    return []

                data = await response.json()

                extract = data.get("extract", "")
                title = data.get("title", "")
                page_url = data.get("content_urls", {}).get("desktop", {}).get("page", "")

                if not extract:
                    return []

                return [{
                    "source": "Wikipedia",
                    "title": title,
                    "text": extract,
                    "url": page_url
                }]
    except Exception:
        return []


# ---------- WEB SCRAPING (SYNC) ----------
def fetch_web_evidence(claim: str):
    evidence = []
    urls = search_web(claim)

    for url in urls:
        text = scrape_article(url)
        if len(text) > 200:
            evidence.append({
                "source": "Web",
                "url": url,
                "text": text
            })

    return evidence
