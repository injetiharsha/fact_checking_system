# evidence/citation_formatter.py

def format_citations(evidence_list):
    citations = []

    for i, ev in enumerate(evidence_list, start=1):
        source = str(ev.get("source", ""))
        url = str(ev.get("url", ""))
        if source == "logic_engine" or url.startswith("internal://"):
            continue
        citations.append(
            f"[{len(citations) + 1}] {source} - {url}"
        )

    return citations
