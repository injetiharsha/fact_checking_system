import hashlib
import json
import os
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

try:
    import trafilatura
except Exception:  # pragma: no cover - optional dependency
    trafilatura = None

try:
    from playwright.sync_api import sync_playwright
except Exception:  # pragma: no cover - optional dependency
    sync_playwright = None


JUNK_URL_PATTERNS = (
    "/search",
    "/tag/",
    "/tags/",
    "/category/",
    "/categories/",
    "?s=",
    "/topics/",
)

JUNK_TEXT_PATTERNS = (
    "search results",
    "related searches",
    "tag archive",
    "category archive",
)

MIN_WORDS = 30


def _normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def _cache_file(cache_dir: str | Path | None, url: str) -> Path | None:
    if not cache_dir:
        return None
    digest = hashlib.sha1((url or "").encode("utf-8")).hexdigest()
    return Path(cache_dir) / f"{digest}.json"


def _read_cache(cache_dir: str | Path | None, url: str) -> dict | None:
    path = _cache_file(cache_dir, url)
    if path is None:
        return None
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_cache(cache_dir: str | Path | None, url: str, payload: dict) -> None:
    path = _cache_file(cache_dir, url)
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _looks_like_junk_url(url: str) -> str | None:
    lowered = (url or "").lower()
    for pattern in JUNK_URL_PATTERNS:
        if pattern in lowered:
            return f"junk_url:{pattern}"
    return None


def _looks_like_junk_text(text: str) -> str | None:
    lowered = (text or "").lower()
    for pattern in JUNK_TEXT_PATTERNS:
        if pattern in lowered:
            return f"junk_text:{pattern}"
    return None


def _extract_with_bs4(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav", "aside", "form"]):
        tag.decompose()
    root = soup.find("article") or soup.find("main") or soup.find("body") or soup
    paragraphs = root.find_all(["p", "li"])
    text = " ".join(p.get_text(" ", strip=True) for p in paragraphs)
    return _normalize_space(text)


def _text_quality(text: str) -> tuple[int, bool]:
    normalized = _normalize_space(text)
    return len(normalized.split()), _looks_like_junk_text(normalized) is None


def _extract_with_trafilatura(html: str, url: str) -> str:
    if trafilatura is None:
        return ""
    extracted = trafilatura.extract(
        html,
        url=url,
        include_comments=False,
        include_tables=False,
        favor_recall=True,
        deduplicate=True,
    )
    return _normalize_space(extracted or "")


def _extract_with_playwright(url: str, timeout: int = 10) -> tuple[str, str]:
    if sync_playwright is None:
        return "", "playwright_unavailable"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="networkidle", timeout=timeout * 1000)
            html = page.content()
            browser.close()
        text = _extract_with_trafilatura(html, url) or _extract_with_bs4(html)
        return text, "playwright"
    except Exception:
        return "", "playwright_failed"


def fetch_and_extract(
    url: str,
    headers: dict,
    timeout: int = 10,
    retries: int = 2,
    verify: bool = True,
    cache_dir: str | Path | None = "logs/extraction_cache",
) -> dict:
    enable_playwright = os.getenv("ENABLE_PLAYWRIGHT_FALLBACK", "0").strip().lower() in {"1", "true", "yes", "on"}
    cached = _read_cache(cache_dir, url)
    if cached is not None:
        cached["cache_hit"] = True
        return cached

    url_reject = _looks_like_junk_url(url)
    if url_reject:
        payload = {
            "url": url,
            "ok": False,
            "text": "",
            "word_count": 0,
            "extractor": "none",
            "reject_reason": url_reject,
            "status_code": None,
            "cache_hit": False,
        }
        _write_cache(cache_dir, url, payload)
        return payload

    response = None
    last_error = None
    for _ in range(max(1, retries)):
        try:
            response = requests.get(url, headers=headers, timeout=timeout, verify=verify)
            break
        except requests.RequestException as exc:
            last_error = exc
            response = None

    if response is None:
        payload = {
            "url": url,
            "ok": False,
            "text": "",
            "word_count": 0,
            "extractor": "none",
            "reject_reason": f"fetch_error:{type(last_error).__name__}" if last_error else "fetch_error",
            "status_code": None,
            "cache_hit": False,
        }
        _write_cache(cache_dir, url, payload)
        return payload

    html = response.text or ""
    status_code = response.status_code
    if status_code != 200 or "html" not in (response.headers.get("Content-Type", "").lower()):
        payload = {
            "url": url,
            "ok": False,
            "text": "",
            "word_count": 0,
            "extractor": "none",
            "reject_reason": f"bad_response:{status_code}",
            "status_code": status_code,
            "cache_hit": False,
        }
        _write_cache(cache_dir, url, payload)
        return payload

    trafilatura_text = _extract_with_trafilatura(html, url)
    bs4_text = _extract_with_bs4(html)
    tf_words, tf_clean = _text_quality(trafilatura_text)
    bs_words, bs_clean = _text_quality(bs4_text)

    if tf_clean and not bs_clean:
        text = trafilatura_text
        extractor = "trafilatura"
    elif bs_clean and not tf_clean:
        text = bs4_text
        extractor = "beautifulsoup"
    elif bs_words > tf_words:
        text = bs4_text
        extractor = "beautifulsoup"
    else:
        text = trafilatura_text or bs4_text
        extractor = "trafilatura" if trafilatura_text else "beautifulsoup"

    word_count = len(text.split())
    reject_reason = None
    if word_count < MIN_WORDS:
        reject_reason = "too_short"
    else:
        reject_reason = _looks_like_junk_text(text)

    if reject_reason is not None and enable_playwright:
        pw_text, pw_state = _extract_with_playwright(url, timeout=timeout)
        if pw_text:
            text = pw_text
            extractor = "playwright"
            word_count = len(text.split())
            reject_reason = None if word_count >= MIN_WORDS else "too_short"
        elif pw_state == "playwright_failed":
            reject_reason = f"{reject_reason}|playwright_failed"

    payload = {
        "url": url,
        "ok": reject_reason is None,
        "text": text if reject_reason is None else "",
        "word_count": word_count,
        "extractor": extractor,
        "reject_reason": reject_reason,
        "status_code": status_code,
        "cache_hit": False,
    }
    _write_cache(cache_dir, url, payload)
    return payload
