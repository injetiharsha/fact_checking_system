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
- regenerates Colab-specific configs automatically before stage 1 and stage 2 with:
  - `batch_size=48`
  - `eval_batch_size=48`
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
1. run the notebook top to bottom (the train cells refresh the Colab configs automatically)
2. finish stage 1
3. run the stage-1 zip cell and optionally download it
4. run stage 2
5. run the final zip cell and download the final archive

What to download if you want a backup in the middle:
- `stance_stage1_public_small.zip`

Stage 2 in Colab now builds the benchmark-driven `stage2_hardcases_v2` dataset before training.

What to download at the end:
- `stance_stage2_hardcases_v2.zip`

After download, place the final checkpoint back into this repo under:
- `checkpoints/stance/stage2_hardcases_v2`

Then enable it with env like:
```env
ENABLE_TRAINED_STANCE=1
STANCE_CHECKPOINT=checkpoints/stance/stage2_hardcases_v2
ENABLE_VERIFIER_V2=1
```


T4 tuning note:
- the notebook now targets `batch_size=48` on a T4
- if Colab throws CUDA out-of-memory, lower both train/eval batch sizes to `32` in the generated config cell

## Relevance Training

Use [notebooks/colab_train_relevance.ipynb](./notebooks/colab_train_relevance.ipynb) on a Google Colab T4.

What it supports:
- rebuilding `v11` in Colab
- rebuilding `v9` in Colab
- optionally rebuilding `v10` if the public AVeriTeC files are present in the repo
- generating a Drive-backed relevance config
- training `v11`, `v9`, or `v10`
- zipping the final relevance checkpoint for download

Recommended order for the T4 time budget:
1. train `v11` first
2. benchmark it locally in this repo
3. if `v11` still misses key Phase 2 claims, try `v9` or a follow-up cleaned variant
4. only then spend time on the larger `v10` public-data run

Relevant configs:
- `training/configs/relevance_v11.yaml`
- `training/configs/relevance_v9.yaml`
- `training/configs/relevance_v10_averitec.yaml`

The notebook generates Colab-specific configs automatically with:
- `batch_size=16`
- `eval_batch_size=16`
- Drive-backed checkpoint and metrics paths

Helper script used by the notebook:
- `training/common/generate_colab_relevance_config.py`

Download note:
- the notebook creates the zip inside the Colab runtime under `/content/<run_name>.zip`
- `files.download(...)` sends that file to your browser, which usually saves it in your local `Downloads` folder unless your browser is configured differently
- if you want to confirm the file exists before downloading, run `!ls -lh /content/*.zip`
