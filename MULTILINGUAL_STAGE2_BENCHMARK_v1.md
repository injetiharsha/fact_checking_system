## Multilingual Stage-2 Benchmark v1

File:
- `benchmark_claims/multilingual_stage2_benchmark_v1.json`

Purpose:
- Compare `relevance v9_run1` against the experimental `relevance v13_stage2_multilingual_run1`
- Focus on the exact area where stage 2 is supposed to help:
  - native-script multilingual claims
  - India official/entity claims
  - March 2026 India live-news claims

Coverage:
- 20 claims
- Languages:
  - Telugu
  - Hindi
  - Tamil
  - Kannada
  - Malayalam
- Mix:
  - geography
  - science
  - India official/entity
  - India live/news

Suggested run:

```powershell
.\.venv\Scripts\python.exe benchmark_multi_test.py --claims-file benchmark_claims\multilingual_stage2_benchmark_v1.json --output logs\multilingual_stage2_benchmark_v1_results.json
```

Suggested comparison:
- Run once with `RELEVANCE_CHECKPOINT=checkpoints/relevance/v9_run1`
- Run once with `RELEVANCE_CHECKPOINT=checkpoints/relevance/v13_stage2_multilingual_run1`
- Keep the rest of the stack fixed:
  - `STANCE_CHECKPOINT=checkpoints/stance/stage2_hardcases_v3_bias`
  - `CLAIM_CHECKABILITY_CHECKPOINT=checkpoints/claim_checkability/v2_run2`
  - recommended runtime settings

What to watch:
- accuracy
- false-positive rate
- neutral rate
- multilingual claims that flipped from `NEUTRAL` to correct verdicts
