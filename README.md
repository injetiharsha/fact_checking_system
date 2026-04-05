# Fact Checking System

Internet-first, real-time fact-checking system built with FastAPI, live web retrieval, local ranking/classification models, and an optional Groq-backed LLM verifier.

## Overview

This project evaluates claims by:

- classifying the claim type and context
- generating live web search queries
- retrieving and scraping evidence from the internet
- ranking passages with local relevance logic and model support
- estimating support, refute, or neutral stance
- aggregating evidence into a final verdict with transparency metadata

The current project direction is real-time fact-checking, not local-corpus-first retrieval.

## Current Status

- runtime mode: internet-first fact-checking
- API server: FastAPI
- verifier: Groq enabled, Ollama optional fallback
- promoted stance checkpoint: `checkpoints/stance/v2_run1`
- promoted relevance checkpoint: `checkpoints/relevance/v2_run1`
- benchmark baseline: [parallel_test_results.json](/abs/path/f:/fact_checking_system/parallel_test_results.json)
- architecture lock: [ARCHITECTURE_LOCK.md](/abs/path/f:/fact_checking_system/ARCHITECTURE_LOCK.md)

## Features

- real-time claim verification from live web sources
- search provider fallback across DuckDuckGo, Tavily, and SerpAPI
- source scraping with `trafilatura` plus fallback extraction
- context-aware query shaping
- multi-passage evidence scoring
- stance classification with model and heuristic fallback
- optional LLM rescue verifier using OpenAI-compatible APIs
- PDF and image analysis endpoints
- translation endpoint for report localization
- benchmark harness for regression tracking

## Architecture

### Core Flow

1. receive a claim or document
2. detect language and normalize input
3. classify claim type and context
4. generate search queries
5. fetch candidate sources from the web
6. scrape and clean source content
7. select and score candidate evidence
8. predict stance for each evidence item
9. optionally verify selected items with an LLM
10. aggregate results into a final verdict

### Main Runtime Components

- [main.py](/abs/path/f:/fact_checking_system/main.py): FastAPI app entrypoint
- [routes.py](/abs/path/f:/fact_checking_system/routes.py): API routes
- [pipeline/claim_pipeline.py](/abs/path/f:/fact_checking_system/pipeline/claim_pipeline.py): main claim-check pipeline
- [pipeline/document_pipeline.py](/abs/path/f:/fact_checking_system/pipeline/document_pipeline.py): PDF and image document flows
- [evidence/router.py](/abs/path/f:/fact_checking_system/evidence/router.py): evidence routing logic
- [evidence/general_search.py](/abs/path/f:/fact_checking_system/evidence/general_search.py): live search backend selection
- [semantic/llm_verifier.py](/abs/path/f:/fact_checking_system/semantic/llm_verifier.py): optional OpenAI-compatible verifier
- [benchmark_multi_test.py](/abs/path/f:/fact_checking_system/benchmark_multi_test.py): 30-claim benchmark harness

### Locked Runtime Stack

The stack currently locked for stability is documented in [ARCHITECTURE_LOCK.md](/abs/path/f:/fact_checking_system/ARCHITECTURE_LOCK.md).

Promoted checkpoints:

- claim type: `checkpoints/claim_type/latest`
- context: `checkpoints/context/latest`
- stance: `checkpoints/stance/v2_run1`
- relevance: `checkpoints/relevance/v2_run1`

## API Endpoints

### `GET /health`

Returns a simple service health response.

### `POST /check`

Check a claim in real time.

Request:

```json
{
  "claim": "Mars has two moons."
}
```

### `POST /analyze_pdf`

Upload and analyze a PDF document.

### `POST /analyze_image`

Upload and analyze an image.

### `POST /translate_report`

Translate a report payload into another language.

## Example Response Shape

Core claim response fields:

```json
{
  "claim": "mars has two moons.",
  "language": "en",
  "evidence": [],
  "final_verdict": "TRUE",
  "confidence": 1.0,
  "conflict_analysis": "Strong Supporting Consensus",
  "citations": [],
  "logical_analysis": {},
  "explanation": "..."
}
```

The actual payload also includes a detailed `transparency` object with:

- routing information
- verifier configuration
- claim type and context decisions
- evidence statistics
- policy flags

## Setup

### 1. Create a virtual environment

```powershell
python -m venv .venv
.venv\Scripts\activate
```

### 2. Install dependencies

```powershell
pip install -r requirements.txt
```

### 3. Configure environment variables

Create `.env` in the project root.

Minimum useful example:

```env
MODEL_CACHE_DIR=F:\fact_checking_system\.venv\model_cache
SEARCH_BACKEND=tavily
TAVILY_API_KEY=your_tavily_key
NEWS_API_KEY=your_news_api_key

ENABLE_LLM_VERIFIER=1
LLM_VERIFIER_PROVIDER=groq
LLM_VERIFIER_API_BASE=https://api.groq.com/openai/v1
LLM_VERIFIER_API_KEY=your_groq_key
LLM_VERIFIER_MODEL=openai/gpt-oss-20b
LLM_VERIFIER_TIMEOUT_SECONDS=45
LLM_VERIFIER_POLICY=neutral_only
LLM_VERIFIER_MAX_ITEMS=3
```

Optional local fallback:

```env
#LLM_VERIFIER_PROVIDER=ollama
#LLM_VERIFIER_API_BASE=http://localhost:11434/v1
#LLM_VERIFIER_API_KEY=ollama
#LLM_VERIFIER_MODEL=qwen2.5:3b
```

## Running The Server

```powershell
.venv\Scripts\python.exe -m uvicorn main:app --reload
```

Open:

- API root: `http://127.0.0.1:8000/`
- docs: `http://127.0.0.1:8000/docs`
- frontend: `http://127.0.0.1:8000/frontend`

## Split Deployment: Vercel Frontend + AWS Backend

This is the recommended deployment model for the current stack.

- Vercel hosts the static frontend from `frontend/`
- AWS hosts the FastAPI backend and model/runtime dependencies
- the frontend calls the backend through `frontend/config.js`

### Why this split

The backend uses OCR, Transformers, live retrieval, and optional LLM verification. That is a much better fit for AWS than Vercel serverless functions.

### Frontend on Vercel

Deploy the `frontend` directory as its own Vercel project.

In Vercel:

- New Project -> Import Git Repository
- Root Directory: `frontend`
- Framework Preset: `Other`
- Build Command: leave empty
- Output Directory: leave empty

Set the backend URL in `frontend/config.js` before deployment:

```js
window.FACTLENS_CONFIG = {
  apiBaseUrl: "https://your-aws-api.example.com",
};
```

The frontend can also run locally with an empty `apiBaseUrl`, which keeps same-origin requests for the local FastAPI app.

### Backend on AWS

Run the FastAPI app on AWS behind HTTPS. A VM, ECS service, or similar long-running compute target is the safest fit.

Minimum backend env additions for split-origin deploys:

```env
CORS_ALLOW_ORIGINS=https://your-vercel-app.vercel.app,https://your-custom-frontend-domain.com
MODEL_CACHE_DIR=/srv/factlens/model_cache

SEARCH_BACKEND=tavily
TAVILY_API_KEY=your_tavily_key
NEWS_API_KEY=your_news_api_key

ENABLE_LLM_VERIFIER=1
LLM_VERIFIER_PROVIDER=groq
LLM_VERIFIER_API_BASE=https://api.groq.com/openai/v1
LLM_VERIFIER_API_KEY=your_groq_key
LLM_VERIFIER_MODEL=openai/gpt-oss-20b
```

Run the backend with:

```powershell
.venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### Security Note

Do not commit real secrets in `.env` or frontend config files. Use Vercel project settings for frontend config management and AWS secret storage for backend keys.

## Model And Search Notes

### Search

The system uses multiple search paths with fallback:

- DuckDuckGo HTML
- Tavily
- SerpAPI

Search routing is controlled by environment variables in the runtime.

### Local Model Support

The runtime still depends on local NLP/model components for:

- sentence embeddings
- relevance scoring
- stance classification
- claim type classification
- context classification

These are local support models, not the main source of factual truth. The truth signal is expected to come from live evidence.

### LLM Verifier

The LLM verifier is optional and acts as a rescue/secondary verifier, not the primary engine.

Supported modes:

- Groq
- OpenAI-compatible APIs
- Ollama local server

## Benchmarking

### Full Benchmark

Run:

```powershell
.venv\Scripts\python.exe benchmark_multi_test.py
```

Output:

- [parallel_test_results.json](/abs/path/f:/fact_checking_system/parallel_test_results.json)

### Small 8-Claim Batch

Run:

```powershell
.venv\Scripts\python.exe batch_tests.py
```

Output:

- [batch_results.json](/abs/path/f:/fact_checking_system/batch_results.json)

### Current Baseline Snapshot

The checked-in baseline currently reports:

- total claims: 30
- correct predictions: 22
- accuracy: 0.733
- neutral rate: 0.200
- false positive rate: 0.033

This baseline should be treated as the comparison point until a clearly better stack is promoted.

## Project Structure

```text
fact_checking_system/
├── main.py
├── routes.py
├── requirements.txt
├── ARCHITECTURE_LOCK.md
├── REQUIREMENTS.md
├── benchmark_multi_test.py
├── batch_tests.py
├── pipeline/
├── evidence/
├── semantic/
├── claim_detection/
├── reasoning/
├── verdict/
├── models/
├── training/
├── frontend/
└── data/
```

## Development Guidance

- keep the runtime internet-first
- do not shift the primary fact-check path to local corpus retrieval
- do not promote new checkpoints without benchmark evidence
- keep context signals out of direct verdict logic
- prefer retrieval and evidence-quality improvements over premature retuning

## Known Limitations

- some failures are still driven by weak or indirect evidence selection
- dynamic websites can scrape poorly without browser fallback
- benchmark misses still include `neutral_despite_evidence` cases
- factual claims with subtle comparative wording can still confuse ranking or stance logic
- live search quality depends on provider availability and internet reliability

## Roadmap

Short-term priorities:

- improve live retrieval quality
- improve source ranking and scraping reliability
- reduce `neutral_despite_evidence`
- validate any future relevance upgrade against the locked baseline

Deferred priorities:

- local-corpus-first retrieval
- new stance promotion
- new relevance promotion without benchmark gains


## License

Add your preferred project license before publishing publicly.
