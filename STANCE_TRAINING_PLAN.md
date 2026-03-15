# Stance Training Plan

## Goal
Two-stage stance training:
1. Stage 1 for breadth using public datasets.
2. Stage 2 for specialization using local hardcases.

Runtime remains internet-first. Training data being local does not change the retrieval architecture.

## Stage 1
Build the public dataset:

```powershell
.\.venv\Scripts\python.exe training\common\build_stance_stage1_public.py
```

Train:

```powershell
.\.venv\Scripts\python.exe training\stance\train.py --config training\configs\stance_stage1_public.yaml
```

Output checkpoint:
`checkpoints/stance/stage1_public`

## Stage 2
Build the hardcase dataset:

```powershell
.\.venv\Scripts\python.exe training\common\build_stance_stage2_hardcases.py
```

Train from the stage-1 checkpoint:

```powershell
.\.venv\Scripts\python.exe training\stance\train.py --config training\configs\stance_stage2_hardcases.yaml
```

Output checkpoint:
`checkpoints/stance/stage2_hardcases`

## Suggested Runtime Promotion
After evaluation, point runtime to the promoted checkpoint:

```env
ENABLE_TRAINED_STANCE=1
STANCE_CHECKPOINT=checkpoints/stance/stage2_hardcases
```

## Notes
- Stage 1 uses FEVER, VitaminC, ANLI, MNLI, and a capped SNLI subset.
- Stage 2 uses the curated hardcases already maintained in the repo.
- `ENABLE_VERIFIER_V2=1` should be used with the new decomposition-aware verifier path.
