from urllib.parse import urlparse, urlunparse


def _normalize_url(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url)
    return urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        "",
        "",
        ""
    ))


def deduplicate(evidence_list):
    seen = set()
    unique = []

    for e in evidence_list:
        source = e.get("source", "")
        url = _normalize_url(e.get("url", ""))

        key = (source, url)
        if key not in seen:
            seen.add(key)
            e["url"] = url
            unique.append(e)

    return unique
