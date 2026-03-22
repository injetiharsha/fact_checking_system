# Best Stacks

Status: release decision note as of 2026-03-22

This file is a short companion to `STACK_DECISION_AND_PHASE_STATUS.md`.
It records the two best stack choices:

- the top raw-performance stack
- the recommended real-time stack
- the latest release-style benchmark artifact for the recommended stack

This file is sanitized.
Do not paste real API keys into it.

## Source Benchmark Matrix

Primary comparison runs:

- `logs/full_stack_benchmarks_2026-03-22_002140/locked_baseline_v2.json`
- `logs/full_stack_benchmarks_2026-03-22_002140/relevance_v9_only.json`
- `logs/full_stack_benchmarks_2026-03-22_002140/combined_experimental_v9_rv2_vv2.json`

## 1. Top Raw-Performance Stack

Use this when the priority is the strongest benchmark score.

Environment:

```env
MODEL_CACHE_DIR=F:\fact_checking_system\.venv\model_cache

ENABLE_TRAINED_STANCE=1
STANCE_CHECKPOINT=checkpoints/stance/v2_run1

ENABLE_TRAINED_RELEVANCE=1
RELEVANCE_CHECKPOINT=checkpoints/relevance/v9_run1

ENABLE_RETRIEVAL_V2=1
ENABLE_VERIFIER_V2=1

ENABLE_LLM_VERIFIER=1
LLM_VERIFIER_POLICY=neutral_only

BENCHMARK_MAX_CONCURRENT=2
```

Artifact:

- `logs/full_stack_benchmarks_2026-03-22_002140/combined_experimental_v9_rv2_vv2.json`

Metrics:

- accuracy: `0.867`
- correct predictions: `26/30`
- neutral rate: `0.033`
- false-positive rate: `0.100`
- false-negative rate: `0.033`
- F1 on `TRUE`: `0.913`

Why it wins:

- best accuracy in the tested matrix
- lowest neutral rate in the tested matrix
- strongest overall benchmark ceiling

Why it is not the default recommendation:

- it changes several layers at once
- it is harder to debug in live web conditions
- its remaining misses still include safety-relevant false positives

## 2. Recommended Real-Time Stack

Use this when the priority is real-time internet fact-checking with lower operational risk.

Environment:

```env
MODEL_CACHE_DIR=F:\fact_checking_system\.venv\model_cache

ENABLE_TRAINED_STANCE=1
STANCE_CHECKPOINT=checkpoints/stance/v2_run1

ENABLE_TRAINED_RELEVANCE=1
RELEVANCE_CHECKPOINT=checkpoints/relevance/v9_run1

ENABLE_RETRIEVAL_V2=0
ENABLE_VERIFIER_V2=0

ENABLE_LLM_VERIFIER=1
LLM_VERIFIER_POLICY=neutral_only

BENCHMARK_MAX_CONCURRENT=2
```

Primary comparison artifact:

- `logs/full_stack_benchmarks_2026-03-22_002140/relevance_v9_only.json`

Latest release-style benchmark artifact:

- `logs/release_style_benchmark_2026-03-22_053057/recommended_stack_release.json`

Metrics:

- accuracy: `0.833`
- correct predictions: `25/30`
- neutral rate: `0.067`
- false-positive rate: `0.100`
- false-negative rate: `0.067`
- F1 on `TRUE`: `0.889`

Why this is the recommended stack:

- it keeps the runtime close to the locked architecture
- most of the observed gain came from the `v9` relevance upgrade itself
- it improves passage selection on noisy scraped pages without turning on extra experimental layers
- it is easier to reason about, compare, and roll back

Release-style benchmark confirmation:

- correct predictions: `25/30`
- accuracy: `0.833`
- neutral rate: `0.067`
- false-positive rate: `0.100`
- false-negative rate: `0.067`
- F1 on `TRUE`: `0.889`

Residual misses in the release-style run:

- `5G networks spread coronavirus` -> `TRUE`
- `The Great Wall of China is visible from space` -> `TRUE`
- `The Amazon River is the longest river in the world` -> `TRUE`
- `Humans share about 50 percent of their DNA with bananas` -> `NEUTRAL`
- `Neptune is the farthest planet from the Sun` -> `NEUTRAL`

## Current Recommendation

If only one stack should be used today, choose:

- `stance v2 + relevance v9 + locked retrieval/verifier path + llm verifier`

That is the best current balance of:

- real-time behavior
- internet-first retrieval
- controlled architecture change
- minimal heuristic growth
