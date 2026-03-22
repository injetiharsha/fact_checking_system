# Phase 5 Multilingual Gate

This note defines the current Phase 5 validation gate for multilingual and India-focused deployment work.

## Purpose

Use this gate after semantic or multilingual fixes to decide whether Phase 5 should:

- stay in semantic-hardening mode, or
- move toward true stance-training preparation

## Runtime Stack

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
PYTHONIOENCODING=utf-8
```

## Claims File

Current multilingual residual gate:

- `benchmark_claims/multilingual_regression_batch_v2.json`

This batch covers:

- Telugu local-admin / farmer-alert phrasing
- Hindi capital-of-India contrasts
- Tamil capital contrasts
- Kannada capital contrasts
- simple multilingual true-claim controls

## Recommended Run Command

Use this PowerShell block from the repo root:

```powershell
$env:PYTHONIOENCODING='utf-8'
$env:MODEL_CACHE_DIR='F:\fact_checking_system\.venv\model_cache'
$env:ENABLE_TRAINED_STANCE='1'
$env:STANCE_CHECKPOINT='checkpoints/stance/v2_run1'
$env:ENABLE_TRAINED_RELEVANCE='1'
$env:RELEVANCE_CHECKPOINT='checkpoints/relevance/v9_run1'
$env:ENABLE_RETRIEVAL_V2='0'
$env:ENABLE_VERIFIER_V2='0'
$env:ENABLE_LLM_VERIFIER='1'
$env:LLM_VERIFIER_POLICY='neutral_only'
$env:BENCHMARK_MAX_CONCURRENT='2'

.\.venv\Scripts\python.exe benchmark_multi_test.py `
  --claims-file benchmark_claims\multilingual_regression_batch_v2.json `
  --output logs\multilingual_regression_batch_v2_results_retry.json
```

This command:

- sets UTF-8 console output
- sets the recommended benchmark env stack
- runs the multilingual batch
- writes a fresh retry artifact under `logs/`

## Decision Rule

After a healthy-network run:

- if failures are still mostly semantic/relation errors, keep Phase 5 in cleanup mode
- if a smaller clean stance-only residual set remains, open Phase 5 training-prep

## Important Note

Do not use a network-failed or search-collapsed run as the Phase 5 decision artifact.

Examples of invalid gate runs:

- most claims return `NEUTRAL` from missing evidence
- search providers are broadly unavailable
- output quality is dominated by connection failures rather than model behavior
