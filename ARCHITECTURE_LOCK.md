## Architecture Lock

Status: locked for real-time fact-checking as of 2026-03-30

This file freezes the promoted runtime architecture so the project can stay stable while the remaining work focuses on retrieval quality, source selection, and smaller residual fixes.

### Locked Runtime Stack

- claim type classifier: `checkpoints/claim_type/latest`
- context classifier: `checkpoints/context/latest`
- stance checkpoint: `checkpoints/stance/stage2_hardcases_v3_bias_restorefast_patch2`
- relevance checkpoint: `checkpoints/relevance/v9_run1`
- claim-checkability checkpoint: `checkpoints/claim_checkability/v2_run2`
- retrieval pipeline: locked internet-first retrieval stack in `pipeline/claim_pipeline.py`
- LLM verifier: enabled, provider `groq`, model `openai/gpt-oss-20b`, policy `neutral_only`

### Why This Is Locked

- `restorefast_patch2` recovered the stance line and passed all three benchmark gates:
  - 30-claim: accuracy `0.867`
  - mixed 50-claim: accuracy `0.820`
  - mixed 68-claim: accuracy `0.794`
- `v9_run1` remains the best practical relevance checkpoint
- `v2_run2` remains the best practical claim-checkability checkpoint
- the main remaining bottleneck is retrieval/source quality, not another broad architecture change

### Lock Rules

- do not promote a new stance checkpoint unless it beats `restorefast_patch2` on the benchmark gates
- do not promote a new relevance checkpoint unless it beats `v9_run1` on the benchmark gates
- keep context classification as retrieval guidance only
- do not move verdict logic onto context signals
- keep real-time web retrieval as the primary evidence path
- do not switch the primary runtime to local corpus or local-RAG-first mode
- preserve current benchmark files as the comparison baseline unless a new run clearly beats them

### Allowed Work During Lock

- retrieval and scraping quality improvements
- evidence source curation
- benchmark reruns for monitoring
- residual-data collection for targeted follow-up training
- bug fixes that do not widen the architecture
- observability and trace improvements

### Not Part Of The Primary Runtime

- multilingual experimental stance/checkability pair as the default runtime
- local trusted corpus as the main fact-check source
- FAISS-first or local-RAG-first verdict flow
- retrieval-v2 promotion
- verifier-v2 promotion

### Resume Condition

Unlock only after a new candidate stack is validated by:

- focused claim checks
- `benchmark_multi_test.py`
- 30-claim benchmark
- mixed 50-claim benchmark
- mixed 68-claim benchmark
- no increase in dangerous false positives
