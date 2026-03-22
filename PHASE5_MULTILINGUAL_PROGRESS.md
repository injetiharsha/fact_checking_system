# Phase 5 Multilingual Progress

Status: checkpoint note as of 2026-03-22

This note records the multilingual residual state before the next healthy-network rerun.

## Purpose

- preserve the best known multilingual benchmark state so far
- separate valid quality runs from later network-collapsed runs
- define what the next Phase 5 multilingual gate should compare against

## Reference Batch

- `benchmark_claims/multilingual_regression_batch_v2.json`

## Valid Comparison Runs

### 1. Recommended Stack Baseline

Artifact:

- `logs/multilingual_regression_v2_2026-03-22_145523/multilingual_regression_batch_v2_results.json`

Metrics:

- accuracy: `0.6`
- correct: `6/10`
- neutral rate: `0.0`
- false-positive rate: `0.4`
- false-negative rate: `0.0`

Residual failures:

- Telugu AP farmer alert -> `TRUE`
- Hindi `Mumbai is the capital of India` -> `TRUE`
- Tamil `Bengaluru is the capital of India` -> `TRUE`
- Kannada `Bengaluru is the capital of India` -> `TRUE`

Interpretation:

- routing was already helping
- the remaining problem was support-side overcommitment on multilingual negative claims

### 2. Raw-Performer Comparison

Artifact:

- `logs/multilingual_regression_v2_raw_2026-03-22_145958/multilingual_regression_batch_v2_raw_results.json`

Metrics:

- accuracy: `0.6`
- correct: `6/10`
- neutral rate: `0.0`
- false-positive rate: `0.4`
- false-negative rate: `0.0`

Interpretation:

- raw performer did not improve multilingual quality
- it only increased runtime cost
- this confirmed that the multilingual issue was not solved by `retrieval_v2` or `verifier_v2`

### 3. Best Semantic-Hardening Run So Far

Artifact:

- `logs/multilingual_regression_v2_fix2_2026-03-22_151007/multilingual_regression_batch_v2_fix2_results.json`

Metrics:

- accuracy: `0.6`
- correct: `6/10`
- neutral rate: `0.2`
- false-positive rate: `0.2`
- false-negative rate: `0.0`

Residual failures:

- Telugu AP farmer alert -> `TRUE`
- Hindi `Mumbai is the capital of India` -> `TRUE`
- Tamil `Bengaluru is the capital of India` -> `NEUTRAL`
- Kannada `Bengaluru is the capital of India` -> `NEUTRAL`

Interpretation:

- this remains the best valid multilingual quality run so far
- false positives were reduced from `4` to `2`
- the India-capital confusion became safer even when not yet fully correct

## Later Non-Comparable Run

Artifact:

- `logs/multilingual_regression_v2_fix4_results.json`

Why it should not be used as the Phase 5 decision artifact:

- broad provider/search failures collapsed retrieval
- most claims went to `NEUTRAL`
- the result reflects live connectivity failure more than model behavior

## Semantic Fixes Added After The Best Valid Run

These fixes are now committed, but still need a healthy-network benchmark rerun:

- context hint matching now uses safer token-boundary matching
- session cache matching is stricter for similar claims
- capital-claim logic-engine injection is suppressed
- capital-relation parsing now handles:
  - alias forms like `Bombay`
  - noisy prefixes
  - `capital city of the Indian state of ...`
  - qualified-capital phrases like `financial capital`

Most important targeted result:

- `Mumbai is the capital of India` now flips to `FALSE` in live targeted pipeline checks

## Next Phase 5 Gate

Run:

- the command in `PHASE5_MULTILINGUAL_GATE.md`

Use the next healthy-network multilingual rerun to answer:

1. Does `Mumbai is the capital of India` now stay `FALSE` in the full batch?
2. Do Tamil/Kannada India-capital negatives move from `NEUTRAL` to `FALSE` or at least stay safer than `TRUE`?
3. Is the Telugu AP farmer alert still the main remaining multilingual false positive?

## Decision Rule

After that rerun:

- if results clearly improve over `fix2`, Phase 5 stays in semantic-hardening mode
- if a small clean stance-only residual set remains, open Phase 5 training-prep
- if network/search collapses again, do not treat that run as a model-quality decision
