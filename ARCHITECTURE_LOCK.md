## Architecture Lock

Status: locked for real-time fact-checking as of 2026-03-15

This file freezes the runtime architecture so the project can stay stable while you improve real-time web fact-checking behavior.

### Locked Runtime Stack

- claim type classifier: `checkpoints/claim_type/latest`
- context classifier: `checkpoints/context/latest`
- stance checkpoint: `checkpoints/stance/v2_run1`
- relevance checkpoint: `checkpoints/relevance/v2_run1`
- retrieval pipeline: internet-first promoted retrieval stack in `pipeline/claim_pipeline.py`
- LLM verifier: enabled, provider `groq`, model `openai/gpt-oss-20b`

### Lock Rules

- do not promote new stance checkpoints during this lock window
- do not promote new relevance checkpoints during this lock window
- keep context classification as retrieval guidance only
- do not move verdict logic onto context signals
- keep real-time web retrieval as the primary evidence path
- do not switch the primary runtime to local corpus or local-RAG-first mode
- keep Ollama as optional fallback only, not the default runtime
- preserve current benchmark file as the comparison baseline unless a new run clearly beats it

### Why This Is Locked

- the repo plans already treat `stance v2` and `relevance v2` as the promoted stack
- current benchmark evidence does not show a clean promotion case for newer checkpoints
- retrieval quality is still the larger bottleneck than architecture choice
- stable behavior is more valuable than fresh tuning while preparing real-time evidence workflows

### Allowed Work During Lock

- search and scraping quality improvements
- evidence source curation
- API and verifier configuration cleanup
- benchmark reruns for monitoring only
- observability and trace improvements
- bug fixes that do not change verdict policy

### Not Part Of The Primary Runtime

- local trusted corpus as the main fact-check source
- local corpus indexing as the main retrieval path
- FAISS-first or local-RAG-first verdict flow
- benchmark reruns for monitoring only

### Deferred Until After The Lock Window

- relevance `v5` promotion decision
- any new stance fine-tune promotion
- retrieval-v2 promotion
- verifier-v2 promotion
- verdict-threshold retuning
- any local-first architecture shift

### Resume Condition

Unlock only after a new candidate stack is validated by:

- focused claim checks
- `benchmark_multi_test.py`
- no increase in dangerous false positives
