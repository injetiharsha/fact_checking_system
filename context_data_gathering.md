# Context Classification Data Preparation Plan

## 1. Data Sources
- Review the following directories for context-labeled data:
  - data/claim_checkability/
  - data/stance/
  - data/trusted_corpus/
  - Any other relevant data folders
- Check for files with context/topic labels (CSV, JSON, or other formats).

## 2. Label Schema
- Use the 13-topic schema from checkpoints/context/config.json.
- Ensure all data labels match this schema exactly.

## 3. Data Gathering Steps
- List all files in the above directories.
- For each file:
  - Inspect columns/fields for claim/context/topic/label.
  - Note the format (CSV, JSON, etc.).
  - Record the number of samples and label distribution.

## 4. Data Cleaning & Standardization
- Standardize columns to: `claim`, `context` (optional), `label`.
- Map all labels to the 13-topic schema.
- Remove or relabel any samples with missing or invalid labels.

## 5. Data Split
- Plan to split the cleaned data into train/validation/test sets (e.g., 80/10/10).

## 6. Documentation
- Document all data sources, cleaning steps, and label mappings in this file.
- Record any issues or gaps in available data.

---

## Data Gathering Log

- [ ] List files in data/claim_checkability/
- [ ] List files in data/stance/
- [ ] List files in data/trusted_corpus/
- [ ] Inspect each file for context/topic labels
- [ ] Summarize findings and next steps
