from app.semantic.encoder import encode

def embed_evidence(evidence_list):
    """
    Adds semantic embeddings to each evidence item.
    """
    embedded = []

    for e in evidence_list:
        text = e.get("text", "")
        if not text:
            continue

        vec = encode(text)
        if vec is None:
            continue

        e["embedding"] = vec
        embedded.append(e)

    return embedded
