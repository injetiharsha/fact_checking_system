# Stack Decision And Phase Status

Status: decision note as of 2026-03-22

This file records:

- the best-performing full-stack benchmark result
- the best low-risk runtime upgrade
- the exact environment settings for both
- why each stack matters
- how far the project has progressed through the execution plan

This file is intentionally sanitized.
Do not paste real API keys into it.

## Benchmark Matrix Source

Full live benchmark runs were saved under:

- `logs/full_stack_benchmarks_2026-03-22_002140`

Primary artifacts:

- `locked_baseline_v2.json`
- `relevance_v9_only.json`
- `retrieval_v2_only.json`
- `verifier_v2_only.json`
- `combined_experimental_v9_rv2_vv2.json`

All runs used the full 30-claim benchmark in `benchmark_multi_test.py` with live retrieval.

## Best Two Stacks

There are two different "best" answers depending on the decision criterion.

### 1. Best Raw Performer

Use this when the priority is the strongest benchmark result.

Environment stack:

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
- precision on `TRUE`: `0.875`
- recall on `TRUE`: `0.955`
- F1 on `TRUE`: `0.913`

Why this stack is the raw performer:

- it delivered the best overall accuracy in the full benchmark matrix
- it also gave the lowest neutral rate in the tested matrix
- it matched the best false-positive rate among the tested stacks
- it reduced `neutral_despite_evidence` cases to `1`

Why this stack is not automatically the default real-time choice:

- it changes multiple layers at once beyond the locked baseline
- when live behavior changes, root-cause analysis becomes harder
- the remaining misses are still safety-relevant false positives:
  - `5G networks spread coronavirus`
  - `The Great Wall of China is visible from space`
  - `The Amazon River is the longest river in the world`

### 2. Best Low-Risk Upgrade

Use this when the priority is the best practical real-time upgrade with the smallest change surface.

Environment stack:

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

Artifact:

- `logs/full_stack_benchmarks_2026-03-22_002140/relevance_v9_only.json`

Metrics:

- accuracy: `0.833`
- correct predictions: `25/30`
- neutral rate: `0.067`
- false-positive rate: `0.100`
- false-negative rate: `0.067`
- precision on `TRUE`: `0.870`
- recall on `TRUE`: `0.909`
- F1 on `TRUE`: `0.889`

Why this stack is the low-risk upgrade:

- it changes only one major checkpoint from the locked baseline: relevance `v2 -> v9`
- it keeps the rest of the runtime closer to the locked architecture
- it captured most of the observed gain without turning on extra experimental layers
- it improved the locked baseline on all three practical top-line signals:
  - accuracy `0.767 -> 0.833`
  - neutral rate `0.100 -> 0.067`
  - false-positive rate `0.133 -> 0.100`

Why this stack is the best real-time fact-check candidate right now:

- the main visible improvement came from better passage selection and evidence survival on live scraped pages
- it keeps the causal story simpler: the gain mostly comes from relevance quality, not multiple interacting runtime toggles
- it is easier to debug, compare, and roll back
- it better matches the project goal of minimal heuristics and controlled architecture change

## Locked Baseline Reference

The current locked baseline stack remains:

```env
MODEL_CACHE_DIR=F:\fact_checking_system\.venv\model_cache

ENABLE_TRAINED_STANCE=1
STANCE_CHECKPOINT=checkpoints/stance/v2_run1

ENABLE_TRAINED_RELEVANCE=1
RELEVANCE_CHECKPOINT=checkpoints/relevance/v2_run1

ENABLE_RETRIEVAL_V2=0
ENABLE_VERIFIER_V2=0

ENABLE_LLM_VERIFIER=1
LLM_VERIFIER_POLICY=neutral_only

BENCHMARK_MAX_CONCURRENT=2
```

Artifact:

- `logs/full_stack_benchmarks_2026-03-22_002140/locked_baseline_v2.json`

Locked baseline metrics:

- accuracy: `0.767`
- correct predictions: `23/30`
- neutral rate: `0.100`
- false-positive rate: `0.133`
- false-negative rate: `0.067`

## Recommendation Summary

If the goal is pure benchmark strength:

- choose the raw performer stack: `v9 + retrieval_v2 + verifier_v2`

If the goal is real-time fact-checking with lower operational risk:

- choose the low-risk upgrade: `locked stack + relevance v9`

Current practical recommendation:

- use the low-risk upgrade as the most suitable real-time stack today
- treat the raw performer as the strongest experimental stack

## How Far We Came In The Execution Plan

The project has moved materially forward.
The repo is no longer at the original "plan only" stage.

### Phase 1: Retrieval Honesty Baseline

Status: materially completed

What happened:

- baseline packet and live trace collection were run
- BM25-style lexical relevance was added to search candidate scoring in `evidence/router.py`
- trace output was improved so rank components are visible
- retrieval ranking became more text-aligned instead of leaning as heavily on authority/domain effects

Evidence of progress:

- Phase 1 mini benchmark improved to `8/8`
- full live benchmark after Phase 1 work was captured and used as the next baseline

Meaning:

- Phase 1 did what it needed to do: make retrieval quality more honest and inspectable

### Phase 2: Relevance Audit And Residual Follow-Up

Status: partially successful, deferred follow-up remains open

What happened:

- `v7` was audited and not promoted
- `v8` was too weak and not promoted
- `v9_run1` emerged as the strongest recent live relevance candidate
- `v11_run1` regressed badly and was rejected
- public-data import support was added, including AVeriTeC-compatible dataset tooling

Important Phase 2 outcomes:

- `v9_run1` residual hard-set result: accuracy `0.75`, neutral rate `0.125`, false-positive rate `0.125`
- `v11_run1` residual hard-set result: accuracy `0.125`, neutral rate `0.875`, false-positive rate `0.0`

Meaning:

- Phase 2 did not produce a fully clean promotion case
- but it did produce a clear best experimental relevance checkpoint: `v9_run1`
- remaining open issues are narrow and known:
  - `Amazon River` support-side false positive risk
  - `bananas` neutral-despite-evidence behavior in some paths

### Phase 3: Passage Retention And Aggregation Cleanup

Status: sufficient for now, paused with deferred edge-case follow-up

What happened:

- document-level consolidation became more trace-visible
- multiple retained passages per document are now visible in runtime traces
- same-document passage survival improved
- aggregation cleanup was tested live
- full-stack comparison runs were executed across baseline and experimental env combinations

What we learned in Phase 3:

- passage preservation and aggregation changes do matter
- trained stance must be explicitly enabled or the system can silently fall back in misleading ways
- `v9` relevance interacts positively with later-stack improvements
- the combined experimental stack currently gives the best benchmark result, but the simpler `v9` upgrade is the better real-time recommendation
- the remaining benchmark misses are not a clean single Phase 3 problem:
  - `5G networks spread coronavirus` includes stance/logic interaction risk
  - `The Great Wall of China is visible from space` is partly an ambiguity/definition case
  - `The Amazon River is the longest river in the world` is partly a disputed-comparison case

Meaning:

- Phase 3 is no longer just "ready to execute"
- it has started, produced evidence, and clarified the next decision boundary
- the structural Phase 3 goal has been met well enough that it should not block Phase 4
- the remaining false positives should be tracked as deferred cleanup, not as a reason to keep expanding Phase 3 indefinitely

### Phase 4: Session-Scoped Retrieval Cache

Status: active, validated, and tuned for near-paraphrase reuse

Meaning:

- caching had been deferred while retrieval quality and evidence handling were still the bigger blockers
- after the narrow Phase 3 review, Phase 4 became the best next active phase
- a supplementary session-scoped retrieval cache is now implemented
- repeated-claim validation shows that live retrieval still executes while the cache remains trace-visible and supplementary

Phase 4 validation artifact:

- `logs/phase4_repeat_claim_validation.json`
- `logs/phase4_similar_claim_validation.json`
- `logs/phase4_similar_claim_validation_post_tuning.json`
- `logs/phase4_broader_repeat_query_validation.json`

Phase 4 validation summary:

- average first pass: `63.804s`
- average second pass: `1.694s`
- average improvement: `62.11s`

Important interpretation:

- this speedup is not only from the new session cache
- it also benefits from existing search, extraction, and model caches
- the key Phase 4 success is architectural:
  - live internet retrieval still runs
  - session cache matches are visible
  - duplicate cached evidence is not injected over live evidence
- after one tuning pass, near-paraphrase reuse is materially better while still remaining conservative on looser misinformation phrasing

Post-tuning similar-claim summary:

- before tuning:
  - matched pairs: `1/4`
  - appended pairs: `1/4`
- after tuning:
  - matched pairs: `3/4`
  - returned pairs: `3/4`
  - appended pairs: `2/4`

Broader repeated-query summary:

- claim count: `10`
- verdict stability: `10/10`
- average first pass: `85.094s`
- average second pass: `1.410s`
- average improvement: `83.684s`
- second-pass matched claims: `9/10`
- second-pass returned claims: `9/10`
- second-pass appended claims: `0/10`

Interpretation:

- the cache generalizes well for exact repeated claims across a broader slice
- verdicts stayed stable across both passes
- cached matches were usually recognized but not appended because live retrieval resurfaced the same strong evidence
- this is the desired internet-first behavior for Phase 4

### Phase 5: Residual Hardening Before Any New Stance Training

Status: started in early semantic-hardening mode, retraining still gated

Meaning:

- the current work has correctly stayed retrieval/relevance/passage-first
- Phase 5 is no longer just a passive gate; it is now doing narrow residual cleanup for multilingual and relation-sensitive failures
- the current residual gate is documented in `PHASE5_RESIDUAL_TAXONOMY.md`
- recent Phase 5 work improved:
  - multilingual routing/context correctness
  - cross-claim session-cache safety
  - capital-relation contradiction handling after translation
- stance retraining should still remain later work unless residual failures are clearly isolated as genuine stance failures after these semantic fixes

## Overall Project Position

The project is now beyond the early retrieval/relevance uncertainty stage.

Most honest summary:

- Phase 1 is effectively done
- Phase 2 produced a provisional winner (`v9`) but still has deferred cleanup
- Phase 3 has produced the needed structural evidence and is now paused with deferred edge-case follow-up
- Phase 4 has passed foundation and similar-claim validation, including one successful tuning pass
- Phase 4 also passed a broader repeated-query validation across a wider 10-claim slice
- Phase 5 has started as residual taxonomy plus multilingual semantic hardening, not as stance retraining

That is meaningful progress toward the project goal:

- real-time
- internet-first
- retrieval-led
- minimal heuristics in critical layers

## Current Best Practical Decision

If a single runtime decision must be made today:

- for experimentation and best benchmark score, use the raw performer stack
- for a more stable real-time internet fact-check setup, use the low-risk upgrade stack

If only one stack should be recommended as the current real-time candidate, choose:

- `stance v2 + relevance v9 + locked retrieval/verifier path + llm verifier`

## Immediate Next Step

Rerun multilingual residual validation on a healthy live network and use that result to decide whether Phase 5 stays semantic-only or becomes a true training-prep phase.

Current practical stop point:

- Phase 4 is already a solid completed foundation
- Phase 5 is now the active phase
- Phase 5 retraining remains gated until a clean stance-only failure set exists

Keep these as deferred non-blocking cleanup items:

- `5G networks spread coronavirus`
- `The Great Wall of China is visible from space`
- `The Amazon River is the longest river in the world`
