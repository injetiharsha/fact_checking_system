# Monitoring Flow

Status: operational monitoring flow as of 2026-03-22

This flow is the current default operating mode for the project:

- stabilize
- evaluate
- monitor

It is intentionally lighter than the earlier phase-building work.
Do not reopen Phase 2 or Phase 3 unless recurring valid evidence justifies it.

## Default Runtime Stack

Use the recommended low-risk stack for monitoring:

```env
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

## Canonical Benchmark Sets

Run these three sets as the standard monitoring cycle:

1. `baseline_30claim`
2. `multilingual_regression`
3. `fresh_realtime`

Use benchmark outputs only if:

- `run_validity.is_valid_comparison == true`

Invalid search-collapsed runs must not drive phase decisions.

## Standard Monitoring Cycle

Run a full cycle from the repo root:

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

.\.venv\Scripts\python.exe scripts\run_monitoring_cycle.py
```

This writes:

- timestamped benchmark artifacts under `logs/monitoring_cycles/...`
- a cycle summary JSON
- `logs/residual_ledger.json`
- `RESIDUAL_LEDGER.md`

## Reuse Existing Artifacts

If you already have valid benchmark outputs, rebuild the ledger without rerunning benchmarks:

```powershell
.\.venv\Scripts\python.exe scripts\run_monitoring_cycle.py `
  --skip-env-check `
  --stack-label recommended_v9 `
  --reuse-baseline logs\phase_reassessment_30claim_recommended_v9.json `
  --reuse-multilingual logs\multilingual_regression_batch_v2_results_retry4.json `
  --reuse-fresh logs\fresh_realtime_batch_2026-03-22_results.json
```

## Residual Policy

Only keep a claim in the active residual list if:

- it appears in at least two valid runs
- on the same stack

Primary-cause buckets used in the ledger:

- `relevance_ranking`
- `retrieval_source_quality`
- `aggregation_or_passage_collapse`
- `semantic_relation_handling`
- `stance_only`
- `invalid_run_excluded`

## Phase Reopen Rule

Do not reopen phases based on one-off failures.

Reopen Phase 2 only if recurring valid runs show a real pattern of:

- `neutral_despite_evidence`
- wrong evidence ranking
- relevance-specific regressions across multiple claims

Reopen Phase 3 only if recurring valid runs show:

- strong contradictory passages retrieved but not surviving
- document collapse hiding decisive evidence
- aggregation repeatedly favoring weaker evidence over stronger contradictory evidence

Until then:

- keep the stack stable
- keep evaluating
- keep monitoring
