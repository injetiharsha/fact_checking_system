# Environment Reference

Status: sanitized reference as of 2026-03-22

This file documents runtime environment variables used by the project.

Security rules for this document:
- never paste real API keys here
- use placeholder values only
- do not copy the contents of `.env` into docs or commits

## Core Runtime Flags

Trained model toggles and checkpoints:

```env
ENABLE_TRAINED_CLAIM_TYPE=0
CLAIM_TYPE_CHECKPOINT=checkpoints/claim_type/latest
CLAIM_TYPE_DEVICE=cpu

ENABLE_TRAINED_CONTEXT=0
CONTEXT_CHECKPOINT=checkpoints/context/latest
CONTEXT_DEVICE=cpu

ENABLE_TRAINED_STANCE=0
STANCE_CHECKPOINT=checkpoints/stance/v2_run1
STANCE_DEVICE=cpu

ENABLE_TRAINED_RELEVANCE=0
RELEVANCE_CHECKPOINT=checkpoints/relevance/v2_run1
RELEVANCE_DEVICE=cpu
```

Pipeline feature flags:

```env
ENABLE_RETRIEVAL_V2=0
ENABLE_VERIFIER_V2=0
ENABLE_LLM_VERIFIER=1
LLM_VERIFIER_POLICY=neutral_only
```

Benchmark control:

```env
BENCHMARK_MAX_CONCURRENT=4
```

Model cache and device helpers:

```env
MODEL_CACHE_DIR=F:\fact_checking_system\.venv\model_cache
TRANSFORMERS_CACHE=F:\fact_checking_system\.venv\model_cache\transformers
STANCE_FOUNDATION_DEVICE=cuda
STANCE_FOUNDATION_MODEL=ynie/roberta-large-snli_mnli_fever_anli_R1_R2_R3-nli
VERIFIER_FOUNDATION_MODEL=ynie/roberta-large-snli_mnli_fever_anli_R1_R2_R3-nli
RELEVANCE_EMBED_DEVICE=cuda
BGE_RERANKER_DEVICE=cuda
RELEVANCE_RERANK_DEVICE=cuda
LOCAL_RAG_DEVICE=cpu
```

## Search And API Keys

Use placeholders only in docs:

```env
SEARCH_BACKEND=tavily
TAVILY_API_KEY=your_tavily_key
NEWS_API_KEY=your_news_api_key
NEWSAPI_ORG_KEY=your_newsapi_org_key
SERPAPI_KEY=your_serpapi_key
OPENFDA_API_KEY=your_openfda_key
NASA_API_KEY=your_nasa_key
```

LLM verifier examples:

```env
ENABLE_LLM_VERIFIER=1
LLM_VERIFIER_PROVIDER=groq
LLM_VERIFIER_API_BASE=https://api.groq.com/openai/v1
LLM_VERIFIER_API_KEY=your_groq_key
LLM_VERIFIER_MODEL=openai/gpt-oss-20b
LLM_VERIFIER_TIMEOUT_SECONDS=45
LLM_VERIFIER_POLICY=neutral_only
LLM_VERIFIER_MAX_ITEMS=3
LLM_VERIFIER_MAX_REQUESTS_PER_MINUTE=30
LLM_VERIFIER_MAX_TOKENS_PER_MINUTE=8000
```

Optional local fallback:

```env
#LLM_VERIFIER_PROVIDER=ollama
#LLM_VERIFIER_API_BASE=http://localhost:11434/v1
#LLM_VERIFIER_API_KEY=ollama
#LLM_VERIFIER_MODEL=qwen2.5:3b
```

## Locked Runtime Env

Use this when you want the repo to follow the currently locked stable stack from `ARCHITECTURE_LOCK.md`.

```env
ENABLE_TRAINED_STANCE=1
STANCE_CHECKPOINT=checkpoints/stance/v2_run1
ENABLE_TRAINED_RELEVANCE=1
RELEVANCE_CHECKPOINT=checkpoints/relevance/v2_run1
ENABLE_VERIFIER_V2=0
ENABLE_RETRIEVAL_V2=0
ENABLE_LLM_VERIFIER=1
LLM_VERIFIER_POLICY=neutral_only
```

Notes:
- locked docs describe `v2_run1` as the promoted stance and relevance stack
- trained stance does not activate unless `ENABLE_TRAINED_STANCE=1` is set explicitly
- trained relevance does not activate unless `ENABLE_TRAINED_RELEVANCE=1` is set explicitly

## Experimental Phase 3 Env

Use this for the current Phase 3 retrieval/passages work.

```env
ENABLE_TRAINED_STANCE=1
STANCE_CHECKPOINT=checkpoints/stance/v2_run1
ENABLE_TRAINED_RELEVANCE=1
RELEVANCE_CHECKPOINT=checkpoints/relevance/v9_run1
ENABLE_VERIFIER_V2=0
ENABLE_RETRIEVAL_V2=0
ENABLE_LLM_VERIFIER=1
LLM_VERIFIER_POLICY=neutral_only
BENCHMARK_MAX_CONCURRENT=2
```

Notes:
- this keeps the locked promoted stance checkpoint
- this swaps in `v9_run1` only as the experimental relevance checkpoint
- this is not the same as promoting `v9`

## Colab Training Env

Typical relevance-training Colab flow does not require the local runtime toggles above.
It mainly needs Drive-backed output paths generated from config files.

For local validation after a Colab run, set:

```env
ENABLE_TRAINED_RELEVANCE=1
RELEVANCE_CHECKPOINT=checkpoints/relevance/v11_run1
```

Or for the current preferred experimental candidate:

```env
ENABLE_TRAINED_RELEVANCE=1
RELEVANCE_CHECKPOINT=checkpoints/relevance/v9_run1
```

## Where These Vars Are Used

Primary env map:
- [config.py](/f:/fact_checking_system/training/common/config.py)

Runtime consumers:
- [claim_type_classifier.py](/f:/fact_checking_system/claim_detection/claim_type_classifier.py)
- [claim_context_classifier.py](/f:/fact_checking_system/claim_detection/claim_context_classifier.py)
- [nli_model.py](/f:/fact_checking_system/models/stance/nli_model.py)
- [relevance.py](/f:/fact_checking_system/evidence/relevance.py)
- [claim_pipeline.py](/f:/fact_checking_system/pipeline/claim_pipeline.py)
- [llm_verifier.py](/f:/fact_checking_system/semantic/llm_verifier.py)
- [benchmark_multi_test.py](/f:/fact_checking_system/benchmark_multi_test.py)

## Important Findings From Recent Runs

- Some recent Phase 3 runs accidentally measured fallback stance behavior because `ENABLE_TRAINED_STANCE` was not set.
- `checkpoints/stance/v2_run1` works through the trained subprocess path when enabled.
- The cached foundation NLI model is still not loading locally, so logs may still mention fallback for the foundation layer.
- Relevance also requires explicit env enablement; the existence of a checkpoint folder alone does not activate it.

## Safe Practice

- Keep real keys only in local `.env` or secret stores.
- Never paste keys into markdown, notebooks, benchmark outputs, or commit messages.
- If you need to share config, share variable names and placeholder values only.
