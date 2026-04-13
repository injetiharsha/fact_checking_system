# evidence/general_search.py

import os
import json
import hashlib
import time
import unicodedata
from pathlib import Path
from urllib.parse import parse_qs, quote_plus, unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=True)


class SearchEngine:

    def __init__(self):
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        }
        self.timeout = int(os.getenv("SEARCH_TIMEOUT_SECONDS", "12"))
        self._cache = {}
        self.cache_enabled = os.getenv("FACTLENS_CACHE_RETRIEVAL", "0") == "1"
        self.search_backend = (os.getenv("SEARCH_BACKEND") or "").strip().lower()
        self.search_policy = (os.getenv("SEARCH_POLICY") or "hybrid").strip().lower()
        self.tavily_api_keys = self._load_tavily_api_keys()
        self._tavily_key_index = 0
        self.tavily_api_key = self._current_tavily_key()
        self.serpapi_api_key = (os.getenv("SERPAPI_KEY") or "").strip()
        self.cache_dir = Path("logs/search_cache")
        self.usage_log_path = Path("logs/search_provider_usage.jsonl")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.usage_log_path.parent.mkdir(parents=True, exist_ok=True)
        self.last_trace = {}
        self._provider_backoff = {}
        self._connection_error_backoff_seconds = int(os.getenv("SEARCH_PROVIDER_BACKOFF_SECONDS", "180"))
        self._auth_error_backoff_seconds = int(os.getenv("SEARCH_PROVIDER_AUTH_BACKOFF_SECONDS", "900"))
        self._multilingual_prefer_duckduckgo = (os.getenv("MULTILINGUAL_SEARCH_PREFER_DDG") or "1").strip() == "1"

    def _load_tavily_api_keys(self):
        keys = []
        raw_multi = (os.getenv("TAVILY_API_KEYS") or "").strip()
        if raw_multi:
            for item in raw_multi.split(","):
                key = item.strip()
                if key and key not in keys:
                    keys.append(key)
        raw_single = (os.getenv("TAVILY_API_KEY") or "").strip()
        if raw_single and raw_single not in keys:
            keys.append(raw_single)
        return keys

    def _current_tavily_key(self):
        if not self.tavily_api_keys:
            return ""
        return self.tavily_api_keys[self._tavily_key_index % len(self.tavily_api_keys)]

    def _rotate_tavily_key(self):
        if len(self.tavily_api_keys) <= 1:
            return False
        self._tavily_key_index = (self._tavily_key_index + 1) % len(self.tavily_api_keys)
        self.tavily_api_key = self._current_tavily_key()
        return True

    def search(self, query, max_results=15, plan=None):
        normalized_query = self._normalize_query_text(query)
        backend_order = tuple(self._backend_order(normalized_query, plan=plan))
        available_backends = tuple(self.available_backends(normalized_query, plan=plan))
        if not available_backends:
            available_backends = backend_order
        plan_signature = self._plan_signature(plan)
        cache_key = (
            normalized_query.lower(),
            int(max_results),
            available_backends,
            json.dumps(plan_signature, sort_keys=True),
        )
        if self.cache_enabled:
            cached = self._cache.get(cache_key)
            if cached is not None:
                self.last_trace = {
                    "backend_order": list(backend_order),
                    "available_backends": list(available_backends),
                    "selected_backend": "memory_cache",
                    "cache_hit": True,
                }
                return list(cached)
        disk_cached = self._load_disk_cache(normalized_query, max_results, available_backends, plan_signature)
        if disk_cached is not None:
            if self.cache_enabled:
                self._cache[cache_key] = list(disk_cached)
            self.last_trace = {
                "backend_order": list(backend_order),
                "available_backends": list(available_backends),
                "selected_backend": "disk_cache",
                "cache_hit": True,
            }
            return list(disk_cached)

        results = []
        selected_backend = None
        for backend in available_backends:
            try:
                results = self._search_with_backend(backend, normalized_query, max_results=max_results, plan=plan)
                if results:
                    selected_backend = backend
                    self._provider_backoff.pop(backend, None)
                    break
            except Exception as e:
                print(f"Search error [{backend}]: {type(e).__name__}: {e}")
                self._log_usage(backend, normalized_query, 0, f"{type(e).__name__}: {e}")
                self._record_backend_failure(backend, e)

        if self.cache_enabled and results:
            self._cache[cache_key] = list(results)
        if results and selected_backend:
            self._save_disk_cache(normalized_query, max_results, available_backends, plan_signature, results)
            self._log_usage(selected_backend, normalized_query, len(results), "ok")
        self.last_trace = {
            "backend_order": list(backend_order),
            "available_backends": list(available_backends),
            "selected_backend": selected_backend,
            "cache_hit": False,
            "plan": dict(plan_signature),
        }
        return results

    def available_backends(self, query=None, plan=None):
        backend_order = tuple(self._backend_order(query, plan=plan))
        return [
            backend for backend in backend_order
            if not self._provider_in_backoff(backend)
        ]

    def _provider_in_backoff(self, backend):
        row = self._provider_backoff.get(backend)
        if not row:
            return False
        until = float(row.get("until", 0.0))
        if time.time() >= until:
            self._provider_backoff.pop(backend, None)
            return False
        return True

    def _record_backend_failure(self, backend, error):
        until = None
        if isinstance(error, requests.exceptions.ConnectionError):
            until = time.time() + self._connection_error_backoff_seconds
        elif isinstance(error, requests.exceptions.Timeout):
            until = time.time() + self._connection_error_backoff_seconds
        elif isinstance(error, requests.exceptions.HTTPError):
            status_code = getattr(getattr(error, "response", None), "status_code", None)
            if status_code in {401, 403, 429}:
                until = time.time() + self._auth_error_backoff_seconds
        if until is None:
            return
        self._provider_backoff[backend] = {"until": until}

    def _backend_order(self, query=None, plan=None):
        multilingual_native_query = self._multilingual_prefer_duckduckgo and self._is_non_ascii_query(query)
        # Always use hybrid policy: stable APIs first, DDG as last resort
        if (os.getenv("BENCHMARK_PRIMARY_SEARCH_ONLY") or "0").strip() == "1":
            return [self._resolved_backend()]
        if multilingual_native_query:
            if self.tavily_api_key:
                return ["duckduckgo", "serpapi", "tavily"]
            if self.serpapi_api_key:
                return ["duckduckgo", "serpapi"]
            return ["duckduckgo"]
        if self.tavily_api_key:
            return ["tavily", "serpapi", "duckduckgo"]
        if self.serpapi_api_key:
            return ["serpapi", "duckduckgo"]
        return ["duckduckgo"]

    def _resolved_backend(self):
        if self.search_backend in {"tavily", "serpapi", "duckduckgo"}:
            return self.search_backend
        if self.tavily_api_key:
            return "tavily"
        if self.serpapi_api_key:
            return "serpapi"
        return "duckduckgo"

    def _search_with_backend(self, backend, query, max_results=15, plan=None):
        if backend == "tavily":
            if not self.tavily_api_key:
                return []
            return self._search_tavily(query, max_results=max_results, plan=plan)
        if backend == "serpapi":
            if not self.serpapi_api_key:
                return []
            return self._search_serpapi(query, max_results=max_results, plan=plan)
        return self._search_duckduckgo(query, max_results=max_results)

    def _search_tavily(self, query, max_results=15, plan=None):
        plan = plan or {}
        query = self._normalize_query_text(query)
        payload = {
            "api_key": self._current_tavily_key(),
            "query": query,
            "max_results": max(1, min(int(max_results), 20)),
            "search_depth": "basic",
            "include_answer": False,
            "include_raw_content": False,
        }
        recency_days = plan.get("recency_days")
        if recency_days:
            payload["topic"] = "news"
            payload["days"] = max(1, min(int(recency_days), 365))
        try:
            response = requests.post(
                "https://api.tavily.com/search",
                json=payload,
                headers={"Content-Type": "application/json; charset=utf-8", "Accept-Charset": "utf-8", **self.headers},
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as exc:
            status_code = getattr(getattr(exc, "response", None), "status_code", None)
            if status_code in {401, 403, 429} and self._rotate_tavily_key():
                payload["api_key"] = self._current_tavily_key()
                response = requests.post(
                    "https://api.tavily.com/search",
                    json=payload,
                    headers={"Content-Type": "application/json; charset=utf-8", "Accept-Charset": "utf-8", **self.headers},
                    timeout=self.timeout,
                )
                response.raise_for_status()
            else:
                raise
        data = response.json() or {}
        items = []
        for row in data.get("results", [])[:max_results]:
            url = (row.get("url") or "").strip()
            title = (row.get("title") or url).strip()
            if not url or not title:
                continue
            items.append({
                "title": title,
                "url": url,
                "snippet": (row.get("content") or "").strip(),
                "provider": "tavily",
            })
        return items

    def _search_serpapi(self, query, max_results=15, plan=None):
        plan = plan or {}
        query = self._normalize_query_text(query)
        per_page = max(1, min(int(max_results), 10))
        params = {
            "engine": "google",
            "q": query,
            "num": per_page,
            "api_key": self.serpapi_api_key,
        }
        language = str(plan.get("language") or "").strip().lower()
        country = str(plan.get("country") or "").strip().lower()
        if language:
            params["hl"] = language
        if country:
            params["gl"] = country
        tbs = self._serpapi_recency_param(plan.get("recency_days"))
        if tbs:
            params["tbs"] = tbs
        response = requests.get(
            "https://serpapi.com/search.json",
            params=params,
            headers={"Accept-Charset": "utf-8", **self.headers},
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json() or {}
        items = []
        for row in data.get("organic_results", [])[:max_results]:
            url = (row.get("link") or "").strip()
            title = (row.get("title") or url).strip()
            if not url or not title:
                continue
            items.append({
                "title": title,
                "url": url,
                "snippet": (row.get("snippet") or "").strip(),
                "provider": "serpapi",
            })
        return items

    def _search_duckduckgo(self, query, max_results=15):
        results = []
        query = self._normalize_query_text(query)
        search_url = "https://html.duckduckgo.com/html/?q=" f"{quote_plus(query)}"

        response = requests.get(
            search_url,
            headers=self.headers,
            timeout=self.timeout,
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        links = soup.select("a.result__a")

        for link in links[:max_results]:
            href = (link.get("href") or "").strip()
            title = link.get_text(" ", strip=True)

            if not href or not title:
                continue

            results.append({
                "title": title,
                "url": self._normalize_result_url(href),
                "provider": "duckduckgo",
            })

        return results

    @staticmethod
    def _normalize_query_text(query):
        text = str(query or "")
        text = unicodedata.normalize("NFC", text)
        text = text.replace("\u200b", " ").replace("\ufeff", " ")
        return " ".join(text.split())

    @staticmethod
    def _is_non_ascii_query(query):
        text = str(query or "")
        return any(ord(ch) > 127 for ch in text)

    def _normalize_result_url(self, href):
        resolved = urljoin("https://html.duckduckgo.com", href)
        parsed = urlparse(resolved)

        if "duckduckgo.com" not in parsed.netloc:
            return resolved

        query = parse_qs(parsed.query)
        target = query.get("uddg", [None])[0]
        if target:
            return unquote(target)

        return resolved

    def _cache_file_path(self, query, max_results, backend_order, plan_signature=None):
        payload = json.dumps(
            {
                "q": (query or "").strip().lower(),
                "max_results": int(max_results),
                "backends": list(backend_order),
                "plan": dict(plan_signature or {}),
            },
            sort_keys=True,
        )
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]
        return self.cache_dir / f"{digest}.json"

    def _load_disk_cache(self, query, max_results, backend_order, plan_signature=None):
        path = self._cache_file_path(query, max_results, backend_order, plan_signature)
        if not path.exists():
            return None
        try:
            with path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle) or {}
            return payload.get("results") or []
        except Exception:
            return None

    def _save_disk_cache(self, query, max_results, backend_order, plan_signature, results):
        path = self._cache_file_path(query, max_results, backend_order, plan_signature)
        try:
            with path.open("w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "query": query,
                        "max_results": int(max_results),
                        "backends": list(backend_order),
                        "plan": dict(plan_signature or {}),
                        "results": results,
                    },
                    handle,
                    ensure_ascii=False,
                    indent=2,
                )
        except Exception:
            return

    @staticmethod
    def _serpapi_recency_param(recency_days):
        if not recency_days:
            return None
        days = int(recency_days)
        if days <= 1:
            return "qdr:d"
        if days <= 7:
            return "qdr:w"
        if days <= 31:
            return "qdr:m"
        return "qdr:y"

    @staticmethod
    def _plan_signature(plan):
        if not isinstance(plan, dict):
            return {}
        return {
            "language": str(plan.get("language") or "").strip().lower(),
            "country": str(plan.get("country") or "").strip().lower(),
            "region": str(plan.get("region") or "").strip().lower(),
            "recency_days": int(plan.get("recency_days") or 0),
            "intent_tags": list(plan.get("intent_tags") or []),
        }

    def _log_usage(self, backend, query, result_count, status):
        try:
            with self.usage_log_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({
                    "backend": backend,
                    "query": query,
                    "result_count": int(result_count),
                    "status": status,
                }, ensure_ascii=False) + "\n")
        except Exception:
            return
