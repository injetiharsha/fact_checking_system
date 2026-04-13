## Requirements

This project is designed for internet-first, real-time fact-checking. The primary runtime depends on live search, live page retrieval, and optional LLM verification.

### Runtime Mode

- primary mode: real-time web fact-checking
- primary evidence path: search APIs plus scraping
- optional verifier: Groq or another OpenAI-compatible provider
- local models: used for embeddings, relevance, stance, and supporting NLP
- local corpus: optional only, not the primary runtime path

### System Requirements

Minimum practical setup:

- Windows 10 or Windows 11
- Python 3.10
- 16 GB RAM recommended
- NVIDIA GPU optional but helpful
- stable internet connection required for live fact-checking

Recommended setup:

- Python 3.10 in a virtual environment
- NVIDIA RTX GPU for faster local model inference
- SSD storage for cached models
- reliable internet for search, scraping, and optional LLM verification

### Python Dependencies

Core dependencies are listed in [requirements.txt](/abs/path/f:/fact_checking_system/requirements.txt).

Main groups:

- API server: FastAPI, Uvicorn, Pydantic
- ML/NLP: Torch, Transformers, Sentence Transformers, Accelerate
- retrieval and parsing: Requests, BeautifulSoup, lxml, trafilatura
- document processing: pdfplumber, pytesseract, OpenCV
- training and experimentation: datasets, peft, scikit-learn, PyYAML
- optional retrieval extras: FAISS, Playwright, LlamaIndex

### GPU Environment

For a CUDA-enabled local inference environment, use [requirements-gpu.txt](/abs/path/f:/fact_checking_system/requirements-gpu.txt).

Recommended install order on a clean Python 3.10 virtual environment:

```powershell
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
python -m pip install --upgrade --force-reinstall --index-url https://download.pytorch.org/whl/cu121 -r requirements-gpu.txt
```

Why this exists:

- the repo needs a stable CUDA-enabled torch stack
- `transformers`, `sentence-transformers`, `datasets`, `numpy`, and `torchvision` must stay compatible
- ad-hoc package upgrades can silently break CUDA availability or model loading

### External Services

For real-time fact-checking, at least one search path should be configured.

Supported search/backfill services in the repo include:

- Tavily
- SerpAPI
- DuckDuckGo HTML fallback
- News API for trusted news retrieval
- OpenFDA for health/public safety sources
- NASA API for space/astronomy sources

Optional LLM verifier providers:

- Groq
- any OpenAI-compatible API
- Ollama local server as fallback

### Required Environment Variables

Minimum practical configuration:

```env
MODEL_CACHE_DIR=F:\fact_checking_system\.venv\model_cache
SEARCH_BACKEND=tavily
TAVILY_API_KEY=your_tavily_key
NEWS_API_KEY=your_news_api_key
```

Recommended Groq verifier configuration:

```env
ENABLE_LLM_VERIFIER=1
LLM_VERIFIER_PROVIDER=groq
LLM_VERIFIER_API_BASE=https://api.groq.com/openai/v1
LLM_VERIFIER_API_KEY=your_groq_key
LLM_VERIFIER_MODEL=openai/gpt-oss-20b
LLM_VERIFIER_TIMEOUT_SECONDS=45
LLM_VERIFIER_POLICY=neutral_only
LLM_VERIFIER_MAX_ITEMS=3
```

Optional fallback keys:

- `SERPAPI_KEY`
- `OPENFDA_API_KEY`
- `NASA_API_KEY`
- `RAPIDAPI_KEY`

### Network Requirements

The main runtime is internet-dependent.

Required outbound access:

- search providers
- target news and reference websites
- optional verifier endpoint such as Groq

Without internet access:

- live fact-checking quality drops sharply
- local model components may still run
- the system should be treated as degraded

### Current Locked Runtime

The current locked stack is documented in [ARCHITECTURE_LOCK.md](/abs/path/f:/fact_checking_system/ARCHITECTURE_LOCK.md).

Promoted checkpoints:

- claim type: `checkpoints/claim_type/latest`
- context: `checkpoints/context/latest`
- stance: `checkpoints/stance/v2_run1`
- relevance: `checkpoints/relevance/v2_run1`

### Operational Notes

- keep Groq or another verifier optional, not the sole source of truth
- keep context classification as retrieval metadata, not verdict logic
- avoid switching to local-RAG-first mode unless the product direction changes
- benchmark before promoting any new retrieval or model stack
