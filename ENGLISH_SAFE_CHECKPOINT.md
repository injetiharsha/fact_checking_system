**English Safe Checkpoint**

This repository state is the safe English-first milestone before multilingual runtime-logic tuning begins.

Branch at checkpoint:
- `master-recovered-sync`

Checkpoint intent:
- keep the stable English/default runtime behavior intact
- avoid changing the promoted stack while multilingual runtime logic is tuned separately

Runtime stack at this checkpoint:
- `STANCE_CHECKPOINT=checkpoints/stance/stage2_hardcases_v3_bias_restorefast_patch2`
- `RELEVANCE_CHECKPOINT=checkpoints/relevance/v9_run1`
- `CLAIM_CHECKABILITY_CHECKPOINT=checkpoints/claim_checkability/v2_run2`

English benchmark reference:
- 30-claim default-stack run:
  - accuracy `0.867`
  - neutral rate `0.033`
  - false-positive rate `0.000`

Checkpoint policy:
- treat this state as the rollback target for English-safe behavior
- do multilingual work on separate runtime logic changes from this point forward
