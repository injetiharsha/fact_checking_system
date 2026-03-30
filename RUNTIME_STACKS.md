**Runtime Stacks**
Default English-first production stack:
- `STANCE_CHECKPOINT=checkpoints/stance/stage2_hardcases_v3_bias_restorefast_patch2`
- `RELEVANCE_CHECKPOINT=checkpoints/relevance/v9_run1`
- `CLAIM_CHECKABILITY_CHECKPOINT=checkpoints/claim_checkability/v2_run2`

Separate multilingual runtime profile:
- see [.env.multilingual_runtime.example](/f:/fact_checking_system/.env.multilingual_runtime.example)
- use it for runtime logic tuning experiments without changing the default `.env`

Current policy:
- keep the English-first stack as the default committed runtime
- do multilingual work as a separate runtime branch until it beats the mixed benchmarks
