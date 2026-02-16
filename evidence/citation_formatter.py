# evidence/citation_formatter.py

def format_citations(evidence_list):
    citations = []

    for i, ev in enumerate(evidence_list, start=1):
        citations.append(
            f"[{i}] {ev['source']} - {ev['url']}"
        )

    return citations
