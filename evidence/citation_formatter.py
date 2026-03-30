# evidence/citation_formatter.py

def format_citations(evidence_list):
    citations = []

    seen = set()
    for i, ev in enumerate(evidence_list, start=1):
        source = str(ev.get("source", ""))
        url = str(ev.get("url", ""))
        if source == "logic_engine" or url.startswith("internal://"):
            continue
        if not source.strip() or not url.strip():
            continue
        if not (url.startswith("http://") or url.startswith("https://")):
            continue
        key = (source.strip().lower(), url.strip().lower())
        if key in seen:
            continue
        seen.add(key)
        citations.append(
            f"[{len(citations) + 1}] {source} - {url}"
        )

    return citations
