# Project Metrics Summary

## Current Best Runtime Stack

- Relevance: `checkpoints/relevance/v9_run1`
- Stance: `checkpoints/stance/stage2_hardcases_v3_bias_restorefast_patch2`
- Claim checkability: `checkpoints/claim_checkability/v2_run2`
- Retrieval V2: off
- Verifier V2: off
- LLM verifier: on
- Policy: `neutral_only`

## Key Qualified Metrics

### Claim Checkability (`v2_run2`)

Source:
- `training_artifacts/claim_checkability/claim_checkability_metrics.json`
- `logs/claim_checkability_eval_packet_v1_results.json`

Training / evaluation:
- validation accuracy: `0.8976`
- validation weighted F1: `0.8974`
- test accuracy: `0.8795`
- test weighted F1: `0.8795`

Interpretation:
- strong enough for runtime use
- clearly better than heuristic-only claim gating
- still needs better multilingual robustness

### 8-Claim Support-Bias Packet

Source:
- `logs/support_bias_packet_v1_results_v3_bias.json`

Metrics:
- total claims: `8`
- correct: `7`
- accuracy: `0.875`
- neutral rate: `0.125`
- false-positive rate: `0.0`
- blocked count: `0`

Interpretation:
- this was the first strong proof that the stage-2 hardcase stance line materially improved contradiction handling and reduced dangerous false positives

### 30-Claim Benchmark

Primary reference:
- `logs/parallel_test_results_restorefast_patch2.json`

Metrics:
- total claims: `30`
- correct: `26`
- accuracy: `0.867`
- neutral rate: `0.033`
- false-positive rate: `0.000`
- false-negative rate: `0.133`
- F1 on TRUE class: `0.900`

Main failure categories:
- neutral_despite_evidence: `1`
- false_negative_refute_bias: `2`
- false_negative_general: `1`

Interpretation:
- this is the recovered strong 30-claim baseline
- it confirms the `patch2` stance line did not introduce a safety regression

### 50-Claim Mixed Benchmark

Primary reference:
- `logs/robust_mixed_50_restorefast_patch2.json`

Metrics:
- total claims: `50`
- correct: `41`
- raw accuracy: `0.820`
- neutral rate: `0.100`
- false-positive rate: `0.040`
- false-negative rate: `0.080`
- F1 on TRUE class: `0.885`
- blocked-not-checkable count: `2`

Adjusted metrics excluding blocked claims:
- adjusted total: `48`
- adjusted accuracy: `0.854`
- adjusted neutral rate: `0.062`
- adjusted false-positive rate: `0.042`
- adjusted false-negative rate: `0.042`
- adjusted F1 on TRUE class: `0.920`

Main failure categories:
- neutral_despite_evidence: `3`
- false_negative_refute_bias: `2`
- blocked_not_checkable: `2`
- false_positive_support_bias: `1`
- false_positive_numeric: `1`

Interpretation:
- this was the biggest proof that `patch2` improved mixed English + multilingual/native-script behavior
- multilingual/native-script claims still exist as a residual weakness, but no longer dominate the packet

### 68-Claim Mixed Benchmark

Primary reference:
- `logs/claim_seed_100_mixed_v1_benchmark_restorefast_patch2.json`

Metrics:
- total claims: `68`
- correct: `54`
- raw accuracy: `0.794`
- neutral rate: `0.103`
- false-positive rate: `0.059`
- false-negative rate: `0.088`
- F1 on TRUE class: `0.857`
- blocked-not-checkable count: `1`

Adjusted metrics excluding blocked claim:
- adjusted total: `67`
- adjusted accuracy: `0.806`
- adjusted neutral rate: `0.090`
- adjusted false-positive rate: `0.060`
- adjusted false-negative rate: `0.075`
- adjusted F1 on TRUE class: `0.870`

Main failure categories:
- neutral_despite_evidence: `6`
- false_positive_support_bias: `2`
- false_positive_numeric: `2`
- false_negative_refute_bias: `3`
- blocked_not_checkable: `1`

Interpretation:
- this is the best broad qualified benchmark result currently available in the repo
- the dominant remaining weakness is still retrieval/source quality plus a smaller remaining refute-side residual

## What These Metrics Mean Overall

The project has already improved substantially in three important ways:

1. Claim checkability is now genuinely useful and no longer just heuristic-only.
2. The stance line has been recovered and strengthened through `restorefast_patch2`.
3. The recommended runtime stack is stable enough to benchmark and iterate with confidence again.

The main remaining gap is not front-end quality or checkability. It is still:
- evidence retrieval quality
- source selection
- decisive evidence survival

## Practical Bottom Line

The system is now a strong prototype with a stable recovered stack, but not yet a fully optimized fact-checking engine.

Best completed areas:
- claim-checkability gate
- stance bias reduction and recovery
- benchmark discipline

Highest-priority unfinished area:
- retrieval / source quality
