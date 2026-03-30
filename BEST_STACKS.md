# Best Stacks

Status: release decision note as of 2026-03-30

This file is a short companion to `STACK_DECISION_AND_PHASE_STATUS.md`.
It records the current promoted runtime stack and the strongest qualified benchmark artifacts behind it.

This file is sanitized.
Do not paste real API keys into it.

## Current Promoted Stack

Use this as the default runtime unless a future checkpoint clearly beats it.

Environment:

```env
MODEL_CACHE_DIR=F:\fact_checking_system\.venv\model_cache

ENABLE_TRAINED_STANCE=1
STANCE_CHECKPOINT=checkpoints/stance/stage2_hardcases_v3_bias_restorefast_patch2

ENABLE_TRAINED_RELEVANCE=1
RELEVANCE_CHECKPOINT=checkpoints/relevance/v9_run1

ENABLE_TRAINED_CLAIM_CHECKABILITY=1
CLAIM_CHECKABILITY_CHECKPOINT=checkpoints/claim_checkability/v2_run2
CLAIM_CHECKABILITY_DEVICE=cpu

ENABLE_RETRIEVAL_V2=0
ENABLE_VERIFIER_V2=0

ENABLE_LLM_VERIFIER=1
LLM_VERIFIER_POLICY=neutral_only

BENCHMARK_MAX_CONCURRENT=2
```

Primary benchmark artifacts:

- `logs/parallel_test_results_restorefast_patch2.json`
- `logs/robust_mixed_50_restorefast_patch2.json`
- `logs/claim_seed_100_mixed_v1_benchmark_restorefast_patch2.json`

Metrics:

- 30-claim:
  - accuracy: `0.867`
  - neutral rate: `0.033`
  - false-positive rate: `0.000`
  - false-negative rate: `0.133`
  - F1 on `TRUE`: `0.900`
- mixed 50-claim:
  - accuracy: `0.820`
  - adjusted accuracy: `0.854`
  - neutral rate: `0.100`
  - false-positive rate: `0.040`
  - false-negative rate: `0.080`
  - adjusted F1 on `TRUE`: `0.920`
- mixed 68-claim:
  - accuracy: `0.794`
  - adjusted accuracy: `0.806`
  - neutral rate: `0.103`
  - false-positive rate: `0.059`
  - false-negative rate: `0.088`
  - adjusted F1 on `TRUE`: `0.870`

Why this is the promoted stack:

- `restorefast_patch2` recovered the stance line after the missing-checkpoint breakage
- it matched the earlier strong 30-claim performance
- it materially improved the mixed 50-claim and mixed 68-claim packets
- it improved multilingual/native-script behavior without a broad false-positive blow-up

Current recommendation:

- `stance restorefast_patch2 + relevance v9 + checkability v2_run2 + locked retrieval/verifier path + llm verifier`
