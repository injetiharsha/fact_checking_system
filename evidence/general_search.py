# evidence/general_search.py

import os
import json
import hashlib
import time
from pathlib import Path
from urllib.parse import parse_qs, quote_plus, unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from config import TAVILY_API_KEYS


load_dotenv(Path(__file__).resolve().parents[1] / ".env")


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
        self.tavily_api_keys = list(TAVILY_API_KEYS)
        self.tavily_api_key = self.tavily_api_keys[0] if self.tavily_api_keys else (os.getenv("TAVILY_API_KEY") or "").strip()
        self._tavily_key_index = 0
        self.serpapi_api_key = (os.getenv("SERPAPI_KEY") or "").strip()
        self.cache_dir = Path("logs/search_cache")
        self.usage_log_path = Path("logs/search_provider_usage.jsonl")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.usage_log_path.parent.mkdir(parents=True, exist_ok=True)
        self.last_trace = {}
        self._provider_backoff = {}
        self._connection_error_backoff_seconds = int(os.getenv("SEARCH_PROVIDER_BACKOFF_SECONDS", "180"))
        self._auth_error_backoff_seconds = int(os.getenv("SEARCH_PROVIDER_AUTH_BACKOFF_SECONDS", "900"))

    def search(self, query, max_results=15):
        backend_order = tuple(self._backend_order())
        available_backends = tuple(self.available_backends())
        if not available_backends:
            available_backends = backend_order
        cache_key = (
            (query or "").strip().lower(),
            int(max_results),
            available_backends,
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
        disk_cached = self._load_disk_cache(query, max_results, available_backends)
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
                results = self._search_with_backend(backend, query, max_results=max_results)
                if results:
                    selected_backend = backend
                    self._provider_backoff.pop(backend, None)
                    break
            except Exception as e:
                print(f"Search error [{backend}]: {type(e).__name__}: {e}")
                self._log_usage(backend, query, 0, f"{type(e).__name__}: {e}")
                self._record_backend_failure(backend, e)

        if self.cache_enabled and results:
            self._cache[cache_key] = list(results)
        if results and selected_backend:
            self._save_disk_cache(query, max_results, available_backends, results)
            self._log_usage(selected_backend, query, len(results), "ok")
        self.last_trace = {
            "backend_order": list(backend_order),
            "available_backends": list(available_backends),
            "selected_backend": selected_backend,
            "cache_hit": False,
        }
        return results

    def available_backends(self):
        backend_order = tuple(self._backend_order())
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

    def _backend_order(self):
        if (os.getenv("BENCHMARK_PRIMARY_SEARCH_ONLY") or "0").strip() == "1":
            return [self._resolved_backend()]
        policy = self.search_policy
        if policy == "cheap":
            return ["duckduckgo"]
        if policy == "api":
            preferred = self._resolved_backend()
            fallback_order = []
            for candidate in (preferred, "tavily", "serpapi", "duckduckgo"):
                if candidate not in fallback_order:
                    fallback_order.append(candidate)
            return fallback_order
        # hybrid: cheap first, premium only if cheap fails.
        return ["duckduckgo", "tavily", "serpapi"]

    def _resolved_backend(self):
        if self.search_backend in {"tavily", "serpapi", "duckduckgo"}:
            return self.search_backend
        if self.tavily_api_key:
            return "tavily"
        if self.serpapi_api_key:
            return "serpapi"
        return "duckduckgo"

    def _search_with_backend(self, backend, query, max_results=15):
        if backend == "tavily":
            if not self.tavily_api_key:
                return []
            return self._search_tavily(query, max_results=max_results)
        if backend == "serpapi":
            if not self.serpapi_api_key:
                return []
            return self._search_serpapi(query, max_results=max_results)
        return self._search_duckduckgo(query, max_results=max_results)

    def _search_tavily(self, query, max_results=15):
        api_key = self._next_tavily_api_key()
        if not api_key:
            return []
        payload = {
            "api_key": api_key,
            "query": query,
            "max_results": max(1, min(int(max_results), 20)),
            "search_depth": "basic",
            "include_answer": False,
            "include_raw_content": False,
        }
        response = requests.post(
            "https://api.tavily.com/search",
            json=payload,
            headers={"Content-Type": "application/json", **self.headers},
            timeout=self.timeout,
        )
        response.raise_for_status()
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

    def _next_tavily_api_key(self):
        if not self.tavily_api_keys:
            return self.tavily_api_key
        key = self.tavily_api_keys[self._tavily_key_index % len(self.tavily_api_keys)]
        self._tavily_key_index = (self._tavily_key_index + 1) % len(self.tavily_api_keys)
        return key

    def _search_serpapi(self, query, max_results=15):
        per_page = max(1, min(int(max_results), 10))
        response = requests.get(
            "https://serpapi.com/search.json",
            params={
                "engine": "google",
                "q": query,
                "num": per_page,
                "api_key": self.serpapi_api_key,
            },
            headers=self.headers,
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

    def _cache_file_path(self, query, max_results, backend_order):
        payload = json.dumps(
            {
                "q": (query or "").strip().lower(),
                "max_results": int(max_results),
                "backends": list(backend_order),
            },
            sort_keys=True,
        )
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]
        return self.cache_dir / f"{digest}.json"

    def _load_disk_cache(self, query, max_results, backend_order):
        path = self._cache_file_path(query, max_results, backend_order)
        if not path.exists():
            return None
        try:
            with path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle) or {}
            return payload.get("results") or []
        except Exception:
            return None

    def _save_disk_cache(self, query, max_results, backend_order, results):
        path = self._cache_file_path(query, max_results, backend_order)
        try:
            with path.open("w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "query": query,
                        "max_results": int(max_results),
                        "backends": list(backend_order),
                        "results": results,
                    },
                    handle,
                    ensure_ascii=False,
                    indent=2,
                )
        except Exception:
            return

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
