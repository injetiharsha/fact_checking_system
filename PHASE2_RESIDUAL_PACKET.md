# Phase 2 Residual Packet

Status: evaluation packet as of 2026-03-22

This packet now isolates a deployment-oriented India-focused live slice for narrow Phase 2 evaluation.

## Claims File

- `benchmark_claims/phase2_residual_packet_v1.json`

## Purpose

Use this packet to evaluate a small India-focused official-source slice under the recommended stack.
It is better aligned with current live fact-check deployment priorities than the earlier mixed residual set.

Current packet contents:

- `ISRO's START-2026 programme was inaugurated on March 11, 2026.`
- `Registration for ISRO's START-2026 programme stayed open until March 15, 2026.`
- `NSSS-2026 was conducted at NESAC, Umiam, Meghalaya from February 23 to 27, 2026.`
- `The ESA-ISRO Earth observation agreement on March 4, 2026 was signed in person in Ahmedabad.`

## Run Command

Use the recommended stack:

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
  --claims-file benchmark_claims\phase2_residual_packet_v1.json `
  --output logs\phase2_residual_packet_v1_results.json
```

## Decision Use

If this packet stays consistently weak across later valid runs, Phase 2 remains on `reopen_watch`.

If it improves without broader regressions, Phase 2 can return to deferred-follow-up status.
