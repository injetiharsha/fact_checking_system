# Data Provenance Log

This file records every external dataset downloaded or merged into local training
artifacts. Append new entries here whenever public data is introduced.

## Entry Format

- `date`: download or integration date
- `task`: which training phase/task uses it
- `dataset`: dataset identifier
- `provider`: where it was downloaded from
- `access_method`: exact loader call or script path
- `config_or_split`: config name and split used
- `sample_limit`: cap used in this project
- `output_usage`: which local dataset version consumed it
- `purpose`: why it was added

---

## 2026-03-11

### FEVER
- `date`: 2026-03-11
- `task`: stance / NLI training
- `dataset`: `fever`
- `provider`: Hugging Face Datasets
- `source_url`: `https://huggingface.co/datasets/fever`
- `access_method`: `load_dataset("fever", "v1.0", split="paper_dev")`
- `config_or_split`: `v1.0` / `paper_dev`
- `sample_limit`: `2000`
- `output_usage`: `data/stance/v2`
- `purpose`: add fact-check style `SUPPORT / REFUTE / NEUTRAL` examples, especially to improve `REFUTE` coverage

### MultiNLI
- `date`: 2026-03-11
- `task`: stance / NLI training
- `dataset`: `multi_nli`
- `provider`: Hugging Face Datasets
- `source_url`: `https://huggingface.co/datasets/multi_nli`
- `access_method`: `load_dataset("multi_nli", split="validation_matched")`
- `config_or_split`: `validation_matched`
- `sample_limit`: `2000` configured, but no rows were merged in the first successful `data/stance/v2` build
- `output_usage`: `data/stance/v2`
- `purpose`: intended to broaden general entailment / contradiction / neutral reasoning

### Local Project Stance Data
- `date`: 2026-03-11
- `task`: stance / NLI training
- `dataset`: local weak-labeled stance set
- `provider`: project-generated
- `access_method`: built from [data/stance/v1/dataset.jsonl](/f:/fact_checking_system/data/stance/v1/dataset.jsonl)
- `config_or_split`: local merged source
- `sample_limit`: n/a
- `output_usage`: `data/stance/v2`
- `purpose`: preserve project-specific claim/evidence formatting and local pipeline behavior

---

## Rule

If any new public or external dataset is downloaded, add an entry here at the
same time as the code/config change that introduces it.
