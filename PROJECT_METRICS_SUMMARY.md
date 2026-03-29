# Project Metrics Summary

## Current Best Runtime Stack

- Relevance: `checkpoints/relevance/v9_run1`
- Stance: `checkpoints/stance/stage2_hardcases_v3_bias`
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
- this was the strongest proof that `stage2_hardcases_v3_bias` materially improved contradiction handling and reduced dangerous false positives

### 30-Claim Benchmark

Primary reference:
- `logs/phase_reassessment_30claim_recommended_v9.json`

Metrics:
- total claims: `30`
- correct: `23`
- accuracy: `0.767`
- neutral rate: `0.100`
- false-positive rate: `0.133`
- false-negative rate: `0.067`
- F1 on TRUE class: `0.870`
- total time: `154.427s`
- average claim time: `9.937s`

Main failure categories:
- false_positive_support_bias: `3`
- false_positive_numeric: `1`
- neutral_despite_evidence: `3`

Interpretation:
- good enough to show the stack is usable
- still limited by retrieval/evidence behavior on some claims

### 68-Claim Mixed Benchmark

Primary reference:
- `logs/claim_seed_100_mixed_v1_benchmark_results_v3_bias.json`

Metrics:
- total claims: `68`
- correct: `51`
- raw accuracy: `0.750`
- neutral rate: `0.191`
- false-positive rate: `0.044`
- false-negative rate: `0.118`
- F1 on TRUE class: `0.836`
- blocked-not-checkable count: `1`

Adjusted metrics excluding blocked claim:
- adjusted total: `67`
- adjusted accuracy: `0.761`
- adjusted neutral rate: `0.179`
- adjusted false-positive rate: `0.045`
- adjusted false-negative rate: `0.104`
- adjusted F1 on TRUE class: `0.848`

Main failure categories:
- neutral_despite_evidence: `11`
- false_positive_numeric: `2`
- blocked_not_checkable: `1`
- insufficient_evidence: `1`
- false_negative_refute_bias: `1`
- false_positive_support_bias: `1`

Interpretation:
- this is the best broad benchmark checkpoint currently committed
- the dominant remaining weakness is still evidence retrieval / source selection, not the claim-checkability gate

## What These Metrics Mean Overall

The project has already improved substantially in three important ways:

1. Claim checkability is now genuinely useful and no longer just heuristic-only.
2. Support-bias has been reduced meaningfully with the improved stance checkpoint.
3. The recommended runtime stack is stable enough to benchmark and iterate with confidence.

The main remaining gap is not front-end quality or checkability. It is still:
- evidence retrieval quality
- source selection
- decisive evidence survival

## Practical Bottom Line

The system is now a strong prototype with a stable stack, but not yet a fully optimized fact-checking engine.

Best completed areas:
- claim-checkability gate
- stance bias reduction
- benchmark discipline

Highest-priority unfinished area:
- retrieval / source quality
