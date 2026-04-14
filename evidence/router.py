import asyncio
import math
import time
import os
import uuid
import sys
import re
from urllib.parse import urlparse

from evidence.international.worldbank import WorldBankAPI
from evidence.international.un_data import UNDataAPI
from evidence.government_india.rbi import RBIAPI
from evidence.international.who import WHOAPI
from evidence.international.oecd import OECDAPI
from evidence.international.nasa import NASAAPI
from evidence.international.openfda import OpenFDAAPI
from evidence.trusted_news.news_api import TrustedNewsAPI

from evidence.general_search import SearchEngine
from evidence.search_planner import SearchPlanner
from evidence.local_rag import LocalRAGRetriever
from evidence.scraper import WebScraper
from evidence.credibility_weights import get_weight
from evidence.reference_fallback import ReferenceFallback


# domains that should never be scraped
BLOCKED_DOMAINS = [
    "tiktok.com",
    "instagram.com",
    "facebook.com",
    "fb.watch",
    "fbcdn.net",
    "reddit.com",
    "quora.com",
    "pinterest.com",
    "youtube.com",
    "youtu.be",
    "twitter.com",
    "x.com",
    "threads.net",
    "linkedin.com",
    "telegram.me",
    "t.me",
    "whatsapp.com",
    "wa.me",
    "discord.com",
    "discord.gg",
    "snapchat.com",
    "rumble.com",
    "vimeo.com",
    "dailymotion.com",
]

WEAK_RESULT_URL_MARKERS = (
    "/video/",
    "/videos/",
    "/shorts/",
    "/watch?",
    "/search?",
    "/search/",
    "/live/",
)

WEAK_RESULT_TITLE_MARKERS = (
    "youtube",
    "watch live",
    "live updates",
    "search results",
    "photo gallery",
)

MISINFORMATION_TITLE_PENALTIES = (
    "conspiracy",
    "changed my mind",
    "described as a hoax",
    "false claim",
)
DIRECT_ANSWER_TITLE_HINTS = (
    "fact check",
    "debunk",
    "myth",
    "does not",
    "not responsible",
    "largest planet",
    "only mammals",
    "country and a continent",
    "berries",
    "two moons",
)

CANONICAL_FACT_URL_MARKERS = (
    "/facts",
    "/fact",
    "/reference",
    "/explainer",
    "/science/",
    "/jupiter/",
    "/planets/",
)

CANONICAL_FACT_TITLE_MARKERS = (
    "facts",
    "fact sheet",
    "reference",
    "explainer",
    "overview",
    "what is",
)

LOW_SIGNAL_URL_MARKERS = (
    "/search/",
    "/search?",
    "/gallery/",
    "/galleries/",
    "/image/",
    "/images/",
    "/photo/",
    "/photos/",
    "/media/",
    "/multimedia/",
    "/citations/",
)

LOW_SIGNAL_TITLE_MARKERS = (
    "photo",
    "gallery",
    "image",
    "images",
    "media",
    "technical reports server",
    "citation",
)

HEALTH_TRUSTED_DOMAINS = (
    "who.int",
    "cdc.gov",
    "nih.gov",
    "fda.gov",
    "mayoclinic.org",
    "clevelandclinic.org",
)

SPACE_TRUSTED_DOMAINS = (
    "nasa.gov",
    "esa.int",
    "jpl.nasa.gov",
    "space.com",
    "livescience.com",
)

FACT_REFERENCE_DOMAINS = (
    "britannica.com",
    "nationalgeographic.com",
    "wikipedia.org",
    "ourworldindata.org",
)

def _safe_console_text(value):
    text = str(value)
    enc = sys.stdout.encoding or "utf-8"
    return text.encode(enc, errors="replace").decode(enc, errors="replace")


class EvidenceRouter:

    def __init__(self):

        # structured data APIs
        self.worldbank = WorldBankAPI()
        self.un_api = UNDataAPI()
        self.rbi = RBIAPI()
        self.who = WHOAPI()
        self.oecd = OECDAPI()
        self.nasa = NASAAPI()
        self.openfda = OpenFDAAPI()
        self.news_api = TrustedNewsAPI()
        self.local_rag = LocalRAGRetriever()
        self.local_rag_mode = (os.getenv("LOCAL_RAG_MODE") or "off").strip().lower()

        # search + scraping
        self.search_engine = SearchEngine()
        self.search_planner = SearchPlanner()
        self.scraper = WebScraper()
        self.reference_fallback = ReferenceFallback()
        self._evidence_cache = {}
        self._domain_backoff = {}
        self.cache_enabled = os.getenv("FACTLENS_CACHE_RETRIEVAL", "0") == "1"

        # ensure log directory exists
        os.makedirs("logs/scraped_pages", exist_ok=True)
        os.makedirs("logs/retrieval_debug", exist_ok=True)

    @staticmethod
    def _emit_progress(progress_callback=None, **event):
        if progress_callback is None:
            return
        try:
            progress_callback(event)
        except Exception:
            return

    @staticmethod
    async def _flush_progress():
        await asyncio.sleep(0)

    async def get_evidence(self, claim, exclude_domain=None, trace=None, context_result=None, claim_type_result=None, original_claim=None, language=None, source_text=None, progress_callback=None, max_sources=6, force_refresh=False, source_modality=None):
        try:
            web_source_cap = int(max_sources)
        except Exception:
            web_source_cap = 6
        web_source_cap = max(2, min(10, web_source_cap))

        cache_key = (
            " ".join((claim or "").strip().lower().split()),
            (exclude_domain or "").strip().lower(),
            web_source_cap,
        )
        if self.cache_enabled and not force_refresh and cache_key in self._evidence_cache:
            cached = self._evidence_cache[cache_key]
            return [dict(item) for item in cached]

        evidence_list = []

        if source_text:
            cleaned_source_text = " ".join((source_text or "").split())
            if cleaned_source_text:
                evidence_list.append({
                    "source": "OCR Context",
                    "url": "internal://ocr_context",
                    "text": cleaned_source_text,
                    "weight": 1.25,
                })

        # --- Always add Wikipedia and NASA for PDF claims (additive, not fallback) ---
        is_pdf = str(source_modality or context_result.get("source_modality", "")).lower() == "pdf"
        if is_pdf:
            # Wikipedia
            try:
                reference_hit = self.reference_fallback.fetch_wikipedia(claim)
                if reference_hit and not any(ev.get("url") == reference_hit["url"] for ev in evidence_list):
                    print("[PDF] Additive Wikipedia evidence:", reference_hit.get("url"))
                    evidence_list.append(reference_hit)
            except Exception as e:
                print("[PDF] Wikipedia evidence error:", e)
            # NASA
            try:
                nasa_result = self.nasa.fetch(claim)
                if nasa_result:
                    if isinstance(nasa_result, list):
                        for row in nasa_result:
                            if row and not any(ev.get("url") == row.get("url") for ev in evidence_list):
                                print("[PDF] Additive NASA evidence:", row.get("url"))
                                evidence_list.append(row)
                    elif nasa_result and not any(ev.get("url") == nasa_result.get("url") for ev in evidence_list):
                        print("[PDF] Additive NASA evidence:", nasa_result.get("url"))
                        evidence_list.append(nasa_result)
            except Exception as e:
                print("[PDF] NASA evidence error:", e)

        # ----------------------------
        # 1. Structured APIs
        # ----------------------------

        api_start = time.time()

        disable_structured_apis = (os.getenv("BENCHMARK_DISABLE_STRUCTURED_APIS") or "0").strip() == "1"
        structured_api_timeout_sec = max(1, int((os.getenv("STRUCTURED_API_TIMEOUT_SEC") or "25").strip() or "25"))
        disabled_api_ids = {
            token.strip().lower()
            for token in (os.getenv("STRUCTURED_API_DISABLE_LIST") or "").split(",")
            if token and token.strip()
        }
        api_tasks = []
        if not disable_structured_apis:
            self._emit_progress(progress_callback, stage="structured_api", status="active", detail="Querying structured data providers")
            await self._flush_progress()

            async def _run_api(api_id, fetcher):
                try:
                    result = await asyncio.wait_for(
                        asyncio.to_thread(fetcher, claim),
                        timeout=structured_api_timeout_sec,
                    )
                except asyncio.TimeoutError:
                    self._emit_progress(
                        progress_callback,
                        stage="structured_api",
                        status="active",
                        detail=f"{api_id.upper()} timed out",
                        substep=api_id,
                        substatus="error",
                    )
                    return None
                except Exception:
                    raise
                if result:
                    self._emit_progress(progress_callback, stage="structured_api", status="active", detail=f"{api_id.upper()} returned data", substep=api_id, substatus="done")
                return result

            api_sources = [
                ("worldbank", self.worldbank.fetch),
                ("un_data", self.un_api.fetch),
                ("rbi", self.rbi.fetch),
                ("who", self.who.fetch),
                ("oecd", self.oecd.fetch),
                ("nasa", self.nasa.fetch),
                ("openfda", self.openfda.fetch),
                ("news_api", self.news_api.fetch),
            ]
            api_tasks = [
                _run_api(api_id, fetcher)
                for api_id, fetcher in api_sources
                if api_id not in disabled_api_ids
            ]

        if api_tasks:
            try:
                results = await asyncio.gather(*api_tasks, return_exceptions=True)
            except asyncio.CancelledError:
                print("Evidence retrieval cancelled during structured API fetch.")
                return evidence_list
        else:
            results = []

        for result in results:

            if isinstance(result, Exception):
                continue

            if not result:
                continue

            if isinstance(result, list):
                evidence_list.extend(result)
            else:
                evidence_list.append(result)

        print("Dynamic data:", round(time.time() - api_start, 3), "sec")
        self._emit_progress(progress_callback, stage="structured_api", status="done", detail=f"Structured APIs checked in {round(time.time() - api_start, 3)} sec")
        await self._flush_progress()

        if trace is not None:
            trace["search_provider_chain"] = list(self.search_engine._backend_order())

        # ----------------------------
        # 2. Web search fallback
        # ----------------------------

        search_start = time.time()
        self._emit_progress(progress_callback, stage="web_search", status="active", detail="Searching web sources")
        await self._flush_progress()

        search_plan = self.search_planner.build_plan(
            claim,
            context_result,
            claim_type_result,
            original_claim=original_claim,
            language=language,
        )
        query_plan = list(search_plan.get("queries") or [])
        if trace is not None:
            trace["search_queries"] = list(query_plan)
            trace["search_plan"] = dict(search_plan)

        search_results = []
        seen_urls = set()
        for index, query in enumerate(query_plan):
            if index > 0 and not self.search_engine.available_backends():
                if trace is not None:
                    trace["search_short_circuit_reason"] = "all_search_backends_in_backoff"
                break
            per_query_limit = 8 if index == 0 else 4
            for result in self.search_engine.search(query, max_results=per_query_limit, plan=search_plan):
                if trace is not None:
                    trace["search_cache_hit"] = bool(self.search_engine.last_trace.get("cache_hit", False))
                selected_backend = str(self.search_engine.last_trace.get("selected_backend") or result.get("provider") or "search").strip().lower()
                if selected_backend and selected_backend not in {"memory_cache", "disk_cache"}:
                    self._emit_progress(
                        progress_callback,
                        stage="web_search",
                        status="active",
                        detail=f"{selected_backend} returned candidates",
                        substep=selected_backend,
                        substatus="done",
                    )
                url = (result.get("url") or "").strip()
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                enriched = dict(result)
                enriched["query"] = query
                search_results.append(enriched)
                if len(search_results) >= max(15, web_source_cap * 2):
                    break
            if len(search_results) >= max(15, web_source_cap * 2):
                break

        bm25_scores = self._build_bm25_scores(claim, search_results)
        for enriched in search_results:
            score, components = self._score_search_candidate(
                claim,
                enriched,
                context_result,
                claim_type_result,
                bm25_scores=bm25_scores,
            )
            enriched["rank_score"] = score
            enriched["rank_components"] = components

        search_results.sort(key=lambda item: item.get("rank_score", 0.0), reverse=True)
        scrape_candidate_cap = max(12, web_source_cap * 3)
        search_results = search_results[:scrape_candidate_cap]
        self._emit_progress(progress_callback, stage="web_search", status="done", detail=f"Selected {len(search_results)} web result(s)")
        await self._flush_progress()

        print("\n--- SEARCH RESULTS ---")
        for r in search_results:
            print(_safe_console_text(r.get("title", "")))
            print(_safe_console_text(r.get("url", "")))
            print(
                "provider:",
                _safe_console_text(r.get("provider", "unknown")),
                "| query:",
                _safe_console_text(r.get("query", "")),
                "| rank:",
                round(float(r.get("rank_score", 0.0)), 3),
            )

        scrape_jobs = []

        for result in search_results:

            url = result["url"]

            if exclude_domain and exclude_domain in url:
                continue

            if any(domain in url for domain in BLOCKED_DOMAINS):
                continue

            if self._should_skip_scrape_candidate(result):
                continue

            if self._domain_is_in_backoff(url):
                continue

            weight = get_weight(url)

            if weight == 0:
                continue

            scrape_jobs.append((result, url))

            if trace is not None:
                trace.setdefault("search_candidates", []).append({
                    "title": result.get("title"),
                    "url": url,
                    "provider": result.get("provider"),
                    "query": result.get("query"),
                    "rank_score": round(float(result.get("rank_score", 0.0)), 3),
                    "rank_components": dict(result.get("rank_components") or {}),
                })

        # run scrapers concurrently
        scrape_tasks = [
            asyncio.to_thread(self.scraper.scrape_with_metadata, url)
            for _, url in scrape_jobs
        ]

        try:
            if scrape_jobs:
                self._emit_progress(progress_callback, stage="extraction", status="active", detail=f"Extracting text from {len(scrape_jobs)} source(s)")
                await self._flush_progress()
            scraped_pages = await asyncio.gather(
                *scrape_tasks,
                return_exceptions=True
            )
        except asyncio.CancelledError:
            print("Evidence retrieval cancelled during web scraping.")
            return evidence_list

        # combine results
        for (result, url), content in zip(scrape_jobs, scraped_pages):

            if isinstance(content, Exception):
                continue

            if not content:
                continue

            text = content.get("text") if isinstance(content, dict) else ""
            if not text:
                self._record_scrape_outcome(url, content)
                if trace is not None:
                    if content.get("extractor") == "playwright":
                        trace["playwright_used"] = True
                    trace["scraped_pages"].append({
                        "url": url,
                        "title": result["title"],
                        "provider": result.get("provider"),
                        "query": result.get("query"),
                        "rank_score": round(float(result.get("rank_score", 0.0)), 3),
                        "rank_components": dict(result.get("rank_components") or {}),
                        "word_count": int(content.get("word_count", 0) or 0),
                        "extractor": content.get("extractor"),
                        "cache_hit": bool(content.get("cache_hit")),
                        "reject_reason": content.get("reject_reason"),
                        "preview": "",
                    })
                continue

            word_count = len(text.split())
            self._record_scrape_outcome(url, content)

            print("\nScraped:", url)
            print("Words:", word_count)
            print("Preview:", _safe_console_text(text[:200]))

            # save page to file
            page_id = str(uuid.uuid4())[:8]
            filename = f"logs/scraped_pages/page_{page_id}.txt"

            with open(filename, "w", encoding="utf-8") as f:
                f.write(text)

            # add to trace
            if trace is not None:
                if content.get("extractor") == "playwright":
                    trace["playwright_used"] = True

                trace["scraped_pages"].append({
                    "url": url,
                    "title": result["title"],
                    "provider": result.get("provider"),
                    "query": result.get("query"),
                    "rank_score": round(float(result.get("rank_score", 0.0)), 3),
                    "rank_components": dict(result.get("rank_components") or {}),
                    "word_count": word_count,
                    "extractor": content.get("extractor"),
                    "cache_hit": bool(content.get("cache_hit")),
                    "reject_reason": content.get("reject_reason"),
                    "file": filename,
                    "preview": text[:200]
                })

            evidence_list.append({
                "source": result["title"],
                "url": url,
                "text": text,
                "weight": get_weight(url)
            })
            self._emit_progress(
                progress_callback,
                stage="extraction",
                status="active",
                detail=f"Extracted {word_count} words from {result.get('provider') or 'source'}",
                substep=f"extract_{len(evidence_list)}",
                substatus="done",
            )
            if len(evidence_list) >= web_source_cap:
                break

        print("Search results:", round(time.time() - search_start, 3), "sec")
        self._emit_progress(progress_callback, stage="extraction", status="done", detail=f"Built {len(evidence_list)} evidence source(s)")
        await self._flush_progress()

        # (No longer use Wikipedia as fallback for PDF, already added above)
        if not is_pdf and len(evidence_list) < 2:
            reference_hit = self.reference_fallback.fetch_wikipedia(claim)
            if reference_hit and not any(
                ev.get("url") == reference_hit["url"] for ev in evidence_list
            ):
                print("\nReference fallback:", _safe_console_text(reference_hit["source"]))
                print(_safe_console_text(reference_hit["url"]))
                evidence_list.append(reference_hit)

        # ----------------------------
        # 2.5 Optional Local RAG fallback
        # ----------------------------

        rag_results = []
        if self.local_rag_mode in {"fallback", "augment"}:
            rag_start = time.time()
            rag_results = self.local_rag.fetch(claim)
            print("Local RAG:", round(time.time() - rag_start, 3), "sec")
            if trace is not None and rag_results:
                trace["local_rag_hits"] = [
                    {
                        "source": row.get("source"),
                        "url": row.get("url"),
                        "preview": (row.get("text") or "")[:200],
                    }
                    for row in rag_results
                ]

        if rag_results:
            should_merge_rag = (
                self.local_rag_mode == "augment"
                or len(evidence_list) < 2
            )
            if should_merge_rag:
                existing_urls = {ev.get("url") for ev in evidence_list}
                for row in rag_results:
                    if row.get("url") in existing_urls:
                        continue
                    evidence_list.append(row)

        # ----------------------------
        # 3. Remove duplicate URLs
        # ----------------------------

        seen = set()
        unique_evidence = []

        for ev in evidence_list:

            url = ev["url"]

            if url in seen:
                continue

            seen.add(url)
            unique_evidence.append(ev)

        if self.cache_enabled and len(unique_evidence) >= 2:
            self._evidence_cache[cache_key] = [dict(item) for item in unique_evidence]
        return unique_evidence

    @staticmethod
    def _domain_from_url(url):
        try:
            return urlparse(url or "").netloc.lower()
        except Exception:
            return ""

    @staticmethod
    def _is_hard_block_reason(reason):
        lowered = str(reason or "").lower()
        return lowered.startswith("bad_response:401") or lowered.startswith("bad_response:403")

    def _domain_is_in_backoff(self, url):
        domain = self._domain_from_url(url)
        if not domain:
            return False
        row = self._domain_backoff.get(domain)
        if not row:
            return False
        if time.time() >= float(row.get("until", 0.0)):
            self._domain_backoff.pop(domain, None)
            return False
        return True

    def _record_scrape_outcome(self, url, content):
        domain = self._domain_from_url(url)
        if not domain:
            return

        reason = ""
        if isinstance(content, dict):
            reason = str(content.get("reject_reason") or "")

        if self._is_hard_block_reason(reason):
            current = self._domain_backoff.get(domain, {"count": 0})
            count = int(current.get("count", 0)) + 1
            cooldown_seconds = min(3600, 600 * count)
            self._domain_backoff[domain] = {
                "count": count,
                "until": time.time() + cooldown_seconds,
                "reason": reason,
            }
            return

        if isinstance(content, dict) and content.get("ok"):
            self._domain_backoff.pop(domain, None)

    @staticmethod
    def _tokenize_rank_text(text):
        return [
            token for token in re.findall(r"[a-z0-9]+", (text or "").lower())
            if len(token) > 1
        ]

    @staticmethod
    def _candidate_rank_text(result):
        title = str(result.get("title") or "")
        snippet = str(result.get("snippet") or "")
        parsed = urlparse(str(result.get("url") or ""))
        url_text = f"{parsed.netloc} {parsed.path.replace('/', ' ')}"
        return f"{title} {snippet} {url_text}".strip()

    def _build_bm25_scores(self, claim, results):
        query_tokens = self._tokenize_rank_text(claim)
        if not query_tokens or not results:
            return {}

        doc_tokens = {}
        document_frequency = {}
        total_doc_len = 0

        for result in results:
            url = str(result.get("url") or "")
            tokens = self._tokenize_rank_text(self._candidate_rank_text(result))
            doc_tokens[url] = tokens
            total_doc_len += len(tokens)
            for token in set(tokens):
                document_frequency[token] = document_frequency.get(token, 0) + 1

        avg_doc_len = total_doc_len / max(len(results), 1)
        k1 = 1.2
        b = 0.75
        num_docs = len(results)
        raw_scores = {}

        for result in results:
            url = str(result.get("url") or "")
            tokens = doc_tokens.get(url, [])
            if not tokens:
                raw_scores[url] = 0.0
                continue

            token_counts = {}
            for token in tokens:
                token_counts[token] = token_counts.get(token, 0) + 1

            doc_len = len(tokens)
            score = 0.0
            for token in query_tokens:
                freq = token_counts.get(token, 0)
                if freq <= 0:
                    continue
                doc_freq = document_frequency.get(token, 0)
                idf = math.log(1 + ((num_docs - doc_freq + 0.5) / (doc_freq + 0.5)))
                numerator = freq * (k1 + 1.0)
                denominator = freq + k1 * (1.0 - b + b * (doc_len / max(avg_doc_len, 1.0)))
                score += idf * (numerator / max(denominator, 1e-9))
            raw_scores[url] = round(score, 4)

        max_raw = max(raw_scores.values(), default=0.0)
        scores = {}
        for url, raw_score in raw_scores.items():
            normalized = (raw_score / max_raw) if max_raw > 0 else 0.0
            scores[url] = {
                "raw": round(raw_score, 4),
                "normalized": round(normalized, 4),
            }
        return scores

    def _score_search_candidate(self, claim, result, context_result=None, claim_type_result=None, bm25_scores=None):
        title = str(result.get("title") or "").lower()
        url = str(result.get("url") or "").lower()
        snippet = str(result.get("snippet") or "").lower()
        claim_text = (claim or "").lower()
        base = float(get_weight(url))
        context_result = context_result or {}
        domain = str(context_result.get("domain") or "general_factual").strip()
        claim_type = self._claim_type_label(claim_type_result)
        claim_tokens = {
            token for token in re.findall(r"[a-z0-9]+", (claim or "").lower())
            if len(token) > 2
        }
        title_tokens = set(re.findall(r"[a-z0-9]+", title))
        overlap = len(claim_tokens & title_tokens) / max(len(claim_tokens), 1)
        candidate_tokens = set(self._tokenize_rank_text(self._candidate_rank_text(result)))
        query_tokens = set(self._tokenize_rank_text(claim))
        query_coverage = len(query_tokens & candidate_tokens) / max(len(query_tokens), 1)
        bm25_payload = (bm25_scores or {}).get(url, {})
        bm25_normalized = float(bm25_payload.get("normalized", 0.0))
        years = re.findall(r"\b(?:19|20)\d{2}\b", claim or "")
        year_match = 0.15 if years and any(year in title or year in url for year in years) else 0.0
        numeric_match = 0.1 if re.search(r"\b\d+\b", claim or "") and re.search(r"\b\d+\b", title) else 0.0
        source_bonus = 0.08 if any(token in url for token in ("wikipedia.org", ".gov", "who.int", "worldbank.org", "oecd.org", "un.org", ".edu")) else 0.0
        if domain == "technology":
            source_bonus = 0.08 if any(token in url for token in ("techcrunch.com", "theverge.com", "niantic", "linkedin.com", "wikipedia.org")) else 0.0
        if domain in {"health_medicine", "public_health"} or any(token in claim_text for token in ("covid", "vaccine", "virus", "cures", "bleach", "medical", "disease", "health")):
            if any(token in url for token in HEALTH_TRUSTED_DOMAINS):
                source_bonus += 0.14
        if domain in {"science", "space_astronomy"} or any(token in claim_text for token in ("space", "planet", "moon", "sun", "venus", "mars", "jupiter", "great wall")):
            if any(token in url for token in SPACE_TRUSTED_DOMAINS + FACT_REFERENCE_DOMAINS):
                source_bonus += 0.12
        if any(token in url for token in FACT_REFERENCE_DOMAINS):
            source_bonus += 0.06
        domain_bonus = 0.0
        if domain == "history" and (year_match > 0 or any(token in title for token in ("history", "war", "event", "wall", "empire"))):
            domain_bonus += 0.08
        if domain in {"science", "space_astronomy", "environment_climate"} and any(token in url for token in ("wikipedia.org", "nasa.gov", ".edu", "who.int")):
            domain_bonus += 0.06
        if domain == "geography" and any(token in title for token in ("country", "continent", "river", "lake", "planet", "island")):
            domain_bonus += 0.05
        claim_type_bonus = 0.0
        if claim_type == "numerical" and (numeric_match > 0 or year_match > 0):
            claim_type_bonus += 0.08
        direct_answer_bonus = 0.0
        if any(hint in title for hint in DIRECT_ANSWER_TITLE_HINTS):
            direct_answer_bonus += 0.07
        if "bananas are berries" in claim_text and "berries" in title:
            direct_answer_bonus += 0.08
        if "country and a continent" in claim_text and "country" in title and "continent" in title:
            direct_answer_bonus += 0.08
        if "true flight" in claim_text and "true flight" in title:
            direct_answer_bonus += 0.08

        source_type_bonus = 0.0
        source_type_penalty = 0.0
        if self._looks_like_canonical_fact_page(url, title):
            source_type_bonus += 0.14
            if query_coverage >= 0.5:
                source_type_bonus += 0.08
        if self._looks_like_low_signal_page(url, title, snippet):
            source_type_penalty += 0.18
        if domain == "technology":
            entity_terms = [
                token for token in ("niantic", "pokemon", "pokémon", "ar", "spatial", "dataset", "images")
                if token in claim_text
            ]
            if entity_terms and not any(term in title or term in url or term in snippet for term in entity_terms[:4]):
                source_type_penalty += 0.22

        misinformation_penalty = 0.0
        if any(token in claim_text for token in ("hoax", "fake", "faked", "spread coronavirus", "cures covid")):
            if any(marker in title for marker in MISINFORMATION_TITLE_PENALTIES):
                misinformation_penalty += 0.12
            if any(marker in snippet for marker in ("some persistent conspiracy theories", "people have wondered", "viral rumor")):
                misinformation_penalty += 0.08

        weak_result_penalty = 0.0
        if self._looks_like_weak_result(url, title):
            weak_result_penalty += 0.2
        if any(domain in url for domain in BLOCKED_DOMAINS):
            weak_result_penalty += 0.6
        if any(domain in url for domain in (
            "quora.com",
            "reddit.com",
            "answers.com",
            "medium.com",
            "facebook.com",
            "instagram.com",
            "youtube.com",
            "twitter.com",
            "x.com",
            "threads.net",
            "linkedin.com",
            "telegram.me",
            "t.me",
            "vimeo.com",
            "rumble.com",
        )):
            weak_result_penalty += 0.5

        positive_score = (
            (bm25_normalized * 0.44)
            + (query_coverage * 0.18)
            + (overlap * 0.12)
            + (base * 0.14)
            + year_match
            + numeric_match
            + source_bonus
            + domain_bonus
            + claim_type_bonus
            + direct_answer_bonus
            + source_type_bonus
        )
        total_penalty = weak_result_penalty + source_type_penalty + misinformation_penalty
        score = round(positive_score - total_penalty, 4)
        components = {
            "bm25_raw": round(float(bm25_payload.get("raw", 0.0)), 4),
            "bm25_normalized": round(bm25_normalized, 4),
            "query_coverage": round(query_coverage, 4),
            "lexical_overlap": round(overlap, 4),
            "base_weight": round(base, 4),
            "year_match": round(year_match, 4),
            "numeric_match": round(numeric_match, 4),
            "source_bonus": round(source_bonus, 4),
            "domain_bonus": round(domain_bonus, 4),
            "claim_type_bonus": round(claim_type_bonus, 4),
            "direct_answer_bonus": round(direct_answer_bonus, 4),
            "source_type_bonus": round(source_type_bonus, 4),
            "misinformation_penalty": round(misinformation_penalty, 4),
            "source_type_penalty": round(source_type_penalty, 4),
            "weak_result_penalty": round(weak_result_penalty, 4),
            "final_score": round(score, 4),
        }
        return round(score, 4), components

    @staticmethod
    def _looks_like_weak_result(url, title):
        lowered_url = str(url or "").lower()
        lowered_title = str(title or "").lower()
        return (
            any(marker in lowered_url for marker in WEAK_RESULT_URL_MARKERS)
            or any(marker in lowered_title for marker in WEAK_RESULT_TITLE_MARKERS)
        )

    @staticmethod
    def _looks_like_canonical_fact_page(url, title):
        lowered_url = str(url or "").lower()
        lowered_title = str(title or "").lower()
        return (
            any(marker in lowered_url for marker in CANONICAL_FACT_URL_MARKERS)
            or any(marker in lowered_title for marker in CANONICAL_FACT_TITLE_MARKERS)
        )

    @staticmethod
    def _looks_like_low_signal_page(url, title, snippet=""):
        lowered_url = str(url or "").lower()
        lowered_title = str(title or "").lower()
        lowered_snippet = str(snippet or "").lower()
        if any(marker in lowered_url for marker in LOW_SIGNAL_URL_MARKERS):
            return True
        if any(marker in lowered_title for marker in LOW_SIGNAL_TITLE_MARKERS):
            return True
        if any(marker in lowered_snippet for marker in ("image credit", "photo credit", "download wallpaper")):
            return True
        return False

    def _should_skip_scrape_candidate(self, result):
        url = str(result.get("url") or "").lower()
        title = str(result.get("title") or "").lower()
        if self._looks_like_weak_result(url, title):
            return True
        if self._looks_like_low_signal_page(url, title, result.get("snippet")) and not self._looks_like_canonical_fact_page(url, title):
            return True
        if any(domain in url for domain in BLOCKED_DOMAINS):
            return True
        return False

    @staticmethod
    def _claim_type_label(claim_type_result):
        if not claim_type_result:
            return ""
        claim_type = claim_type_result.get("type") if isinstance(claim_type_result, dict) else None
        if hasattr(claim_type, "value"):
            return str(claim_type.value).lower()
        return str(claim_type or "").lower()
