# Relevance Two-Stage Multilingual Plan

This path separates semantic learning from multilingual surface-form adaptation.

## Stage 1: Converted Multilingual + Broad English

Purpose:
- learn claim/evidence relevance relations in a semantically consistent space
- use English-converted India multilingual news and official-source examples
- keep broad public and residual diversity from `v9`, `v12`, and `AVeriTeC`

Config:
- `training/configs/relevance_v13_stage1_converted.yaml`

Output checkpoint:
- `checkpoints/relevance/v13_stage1_converted_run1`

## Stage 2: Native Multilingual Surface Forms

Purpose:
- adapt the stage-1 model to real multilingual claim/evidence strings
- teach native-script matching across Hindi, Tamil, Telugu, Kannada, and Malayalam
- preserve the semantic structure learned in stage 1

Inputs:
- full stage-1 dataset from `data/relevance/v13_broad`
- native multilingual seed file `data/relevance/seeds/india_multilingual_native_v13.jsonl`

Builder:
- `training/common/build_relevance_v13_stage2_multilingual.py`

Config:
- `training/configs/relevance_v13_stage2_multilingual.yaml`

Output checkpoint:
- `checkpoints/relevance/v13_stage2_multilingual_run1`

## Build Stage 2 Dataset

```powershell
.\.venv\Scripts\python.exe training\common\build_relevance_v13_stage2_multilingual.py
```

## Train Order

```powershell
.\.venv\Scripts\python.exe training\relevance\train.py --config training\configs\relevance_v13_stage1_converted.yaml
.\.venv\Scripts\python.exe training\common\build_relevance_v13_stage2_multilingual.py
.\.venv\Scripts\python.exe training\relevance\train.py --config training\configs\relevance_v13_stage2_multilingual.yaml
```

## Policy

- keep `v9_run1` in runtime until stage 1 or stage 2 clearly beats it
- stage 1 improves semantic grounding
- stage 2 improves multilingual surface-form understanding
- neither stage should be promoted without benchmark comparison
