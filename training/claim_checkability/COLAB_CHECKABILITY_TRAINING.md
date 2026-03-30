# Claim Checkability Colab Training

Use this after `data/claim_checkability/v2` has grown beyond the current seed-only scale.

Recommended base config:

- `training/configs/claim_checkability.yaml`

## Why Colab Helps Later

Use Colab when:

- `v2` has a few hundred to a thousand rows
- you want Drive-backed checkpoints
- you want a repeatable GPU-backed run without local setup friction

Colab is optional for the current tiny prototype dataset.

## Generate A Colab Config

From the repo root in Colab:

```python
!python training/common/generate_colab_claim_checkability_config.py \
  --base-config training/configs/claim_checkability.yaml \
  --use-drive 1 \
  --drive-dir /content/drive/MyDrive/fact_checking_system_colab
```

This creates:

- `training/configs/claim_checkability_colab.yaml`

The generated config uses:

- Drive-backed checkpoints
- Drive-backed metrics output
- `batch_size=32`
- `eval_batch_size=32`
- `fp16=true`

## Train In Colab

```python
!python training/claim_checkability/train.py \
  --config training/configs/claim_checkability_colab.yaml
```

## Suggested Colab Workflow

1. Mount Google Drive
2. Clone the repo
3. Build or upload `data/claim_checkability/v2`
4. Generate the Colab config
5. Run training
6. Copy the final checkpoint back into this repo under:
   - `checkpoints/claim_checkability/<run_name>`

## Runtime Enablement After Training

Use env like:

```env
ENABLE_TRAINED_CLAIM_CHECKABILITY=1
CLAIM_CHECKABILITY_CHECKPOINT=checkpoints/claim_checkability/v1_run1
CLAIM_CHECKABILITY_DEVICE=cpu
```

Keep the heuristic fallback in place until the trained model clearly beats it on:

- short factual claims
- personal statements
- opinions
- questions
- India-focused noisy/social inputs
