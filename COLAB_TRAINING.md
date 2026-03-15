# Colab Training

Use [notebooks/colab_train_stance_small.ipynb](./notebooks/colab_train_stance_small.ipynb) on a Google Colab T4.

Default repo values already set in the notebook:
- `REPO_URL=https://github.com/injetiharsha/fact_checking_system.git`
- `BRANCH=feat/reduce-heuristics-phased`

What the notebook now does:
- mounts Google Drive
- clones the repo safely into `/content`
- installs Colab-safe training dependencies
- builds `stage1_public_small`
- creates Colab-specific configs with:
  - `batch_size=32`
  - `eval_batch_size=32`
  - `max_length=256`
  - `fp16=true`
  - step checkpointing
- saves checkpoints and metrics to Google Drive
- lets you zip and download stage-1 or final stage-2 outputs

Why this is safer for free Colab sessions:
- checkpoints are saved during training, not only at the end
- outputs are written to Google Drive, so session loss does not wipe everything
- you can download a stage-1 backup before starting stage 2

Recommended flow:
1. run the notebook top to bottom
2. finish stage 1
3. run the stage-1 zip cell and optionally download it
4. run stage 2
5. run the final zip cell and download the final archive

What to download if you want a backup in the middle:
- `stance_stage1_public_small.zip`

What to download at the end:
- `stance_stage2_hardcases_small.zip`

After download, place the final checkpoint back into this repo under:
- `checkpoints/stance/stage2_hardcases_small`

Then enable it with env like:
```env
ENABLE_TRAINED_STANCE=1
STANCE_CHECKPOINT=checkpoints/stance/stage2_hardcases_small
ENABLE_VERIFIER_V2=1
```
