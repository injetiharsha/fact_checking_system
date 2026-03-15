Local trusted corpus for the optional retrieval-first RAG path.

Put `.txt` or `.md` files here with high-signal reference content.

Recommended sources:
- NASA
- WHO
- UN
- World Bank
- OECD
- RBI
- MOSPI
- PIB
- official government pages

Suggested metadata pattern at the top of each file:

Source: NASA
URL: https://science.nasa.gov/mars/moons/
Title: Mars Moons

Then include the trusted passage text below.

Runtime flags:
- `ENABLE_LOCAL_RAG=1`
- `LOCAL_RAG_CORPUS_DIR=data/trusted_corpus`
- `LOCAL_RAG_TOP_K=3`
- `LOCAL_RAG_EMBED_MODEL=BAAI/bge-small-en-v1.5`

Required optional packages for this path:
- `llama-index-core`
- `llama-index-embeddings-huggingface`
