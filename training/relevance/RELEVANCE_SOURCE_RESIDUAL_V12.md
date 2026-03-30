# Relevance Source Residual v12

This dataset is a narrow residual scaffold for retrieval/evidence ranking failures where:

- a good authoritative source exists
- a weaker derivative or off-target source wins
- or a decisive sentence is present but not selected strongly enough

## Goal

Improve evidence selection with learned ranking data instead of adding more pipeline heuristics.

## Current focus claims

- `DNA is shaped like a double helix`
- `Jupiter is the largest planet in the solar system`
- `Lake Baikal is the deepest lake on Earth`
- `The Pacific Ocean is the largest ocean on Earth`
- `The Indian Space Research Organisation is commonly known by the acronym ISRO`
- `The Election Commission of India is a private company`
- `Penguins can fly long distances over the ocean`
- `The Titanic completed its first voyage successfully`

## Build

```powershell
.\.venv\Scripts\python.exe training\common\build_relevance_v12_source_residual.py
```

Output:

- `data/relevance/v12_source_residual/train.jsonl`
- `data/relevance/v12_source_residual/validation.jsonl`
- `data/relevance/v12_source_residual/test.jsonl`
- `data/relevance/v12_source_residual/dataset.jsonl`
- `data/relevance/v12_source_residual/metadata.json`

## Record shape

Each record follows the repo's existing relevance training format:

- `claim`
- `candidate_sentence`
- `label`
- `source`
- `source_url`
- `selection_origin`

## How to grow it

For each benchmark residual:

1. capture one decisive sentence that should win as `label=1`
2. capture one or two topical but non-decisive sentences as `label=0`
3. keep the source URL so provenance stays explicit

This should be merged into a broader relevance refresh, not trained as a standalone final model.
