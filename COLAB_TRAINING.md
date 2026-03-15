# Colab Training

Use [notebooks/colab_train_stance_small.ipynb](./notebooks/colab_train_stance_small.ipynb) on a Google Colab T4.

Default repo values already set in the notebook:
- `REPO_URL=https://github.com/injetiharsha/fact_checking_system.git`
- `BRANCH=feat/reduce-heuristics-phased`

What to change first:
- only change `REPO_URL` or `BRANCH` if you want a different repo/branch
- keep `USE_DRIVE = True` if you want the archive copied to Google Drive

What it trains:
- `stage1_public_small`
- `stage2_hardcases_small`

What it downloads at the end:
- `stance_stage2_hardcases_small.zip`

What is inside that zip:
- `checkpoints/stance/stage2_hardcases_small`
- `training_artifacts/stance/stage2_hardcases_small`

After download, place the checkpoint back into this repo under:
- `checkpoints/stance/stage2_hardcases_small`

Then enable it with env like:
```env
ENABLE_TRAINED_STANCE=1
STANCE_CHECKPOINT=checkpoints/stance/stage2_hardcases_small
ENABLE_VERIFIER_V2=1
```
