# Deployment Readiness

Status: 2026-03-22

This note summarizes whether the current system is deployable, under what conditions, and which stack should be used.

This file is sanitized.
Do not paste real API keys into it.

## Short Answer

Yes, the system is deployable as a:

- beta
- internal tool
- monitored demo
- human-reviewed fact-check assistant

No, it is not yet ready to be treated as:

- a fully trusted autonomous public fact-check service
- a high-stakes no-review medical or policy verdict engine
- a fully production-hardened large-scale deployment

## Recommended Deployment Stack

Use the recommended real-time stack:

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

For benchmark stability, a split-device profile is also reasonable:

```env
STANCE_DEVICE=cpu
STANCE_FOUNDATION_DEVICE=cuda
RELEVANCE_DEVICE=cpu
RELEVANCE_EMBED_DEVICE=cuda
BGE_RERANKER_DEVICE=cpu
```

## Why This Stack

This is still the best deployment choice because it gives:

- simpler runtime behavior
- fewer moving parts than the raw performer
- lower operational risk
- faster real-time behavior on the fresh 12-claim batch

The raw performer remains useful for experimentation, but it did not outperform the recommended stack on the fresh real-time batch.

## Current Evidence

### Older 30-Claim Benchmark

Recommended stack:

- accuracy: `0.833`
- false-positive rate: `0.100`
- neutral rate: `0.067`

Raw performer:

- accuracy: `0.867`
- false-positive rate: `0.100`
- neutral rate: `0.033`

Meaning:

- raw performer is still the best score chaser on the older benchmark set

### Fresh 12-Claim Real-Time Batch

Artifacts:

- `logs/fresh_realtime_compare_2026-03-22_141058/recommended_stack.json`
- `logs/fresh_realtime_compare_2026-03-22_141058/raw_performer_stack.json`

Recommended stack:

- accuracy: `0.583`
- correct: `7/12`
- total time: `64.986s`

Raw performer:

- accuracy: `0.583`
- correct: `7/12`
- total time: `78.829s`

Meaning:

- same quality on this fresher real-time set
- recommended stack is faster
- the extra raw-performer layers are not justified as a deployment default right now

## What Is Good Enough Now

The system is now good enough for:

- controlled beta deployment
- internal investigative use
- source-assisted fact-check review
- monitored user-facing demos with clear caveats

The system is not yet strong enough for:

- unattended public verdict publishing
- legal, medical, or policy reliance without human review
- claims where a wrong support verdict would have significant downstream harm

## Main Remaining Risks

- support-side false positives still exist
- some current-event claims become neutral despite decent evidence
- retrieval remains the largest runtime bottleneck
- long-run benchmark robustness still needs more validation
- official-source claims can still be misread when wording is ambiguous or comparative

## Recommended Guardrails If Deployed

- always show the evidence sources and snippets
- keep confidence visible
- label the system as beta or assistant-grade
- require human review for sensitive claims
- log failures and collect residual examples for future refinement
- prefer abstention over overconfident unsupported claims in high-risk contexts

## Operational Recommendation

If deployed now:

- deploy the recommended stack
- keep monitoring on
- collect residual failures
- do not switch the default to the raw performer yet

## Bottom Line

The current system is deployable in a controlled beta sense.

It is not yet fully production-hardened for high-stakes autonomous fact-checking.

If only one stack should be deployed today, use:

- `stance v2 + relevance v9 + locked retrieval/verifier path + llm verifier`
