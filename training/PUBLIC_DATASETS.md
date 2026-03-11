## Public Dataset Types For This Project

Use public data only where local data is too small or too imbalanced.

### Stance / NLI datasets

These are the most useful public datasets for the project because they teach the
model how a claim relates to evidence.

Expected normalized format:

```json
{"claim": "...", "evidence": "...", "label": "SUPPORT"}
```

Supported sources in the current augmentation script:

1. `fever`
- Type: fact-checking claim/evidence dataset
- Helps: support vs refute vs not-enough-info reasoning
- Best use in this project: strengthen `REFUTE` and `NEUTRAL`

2. `multi_nli`
- Type: natural language inference dataset
- Helps: general contradiction / entailment / neutral reasoning
- Best use in this project: broaden stance coverage when local data is too small

3. `allenai/scifact`
- Type: scientific claim/evidence dataset
- Helps: support / contradict with evidence-heavy writing
- Best use in this project: science and health claim behavior

### Why this helps the project

The runtime system must decide whether an evidence sentence:
- supports a claim
- refutes a claim
- or is neutral

Public stance/NLI datasets improve that reasoning before local adaptation.

### Important constraint

Public data should not replace local data. It should only bootstrap the model,
then the model should be adapted again using the project's own claim/evidence
format.
