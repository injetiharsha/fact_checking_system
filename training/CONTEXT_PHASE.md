# Context Phase

This phase adds a retrieval-oriented claim context layer.

Current scope:
- train top-level domain classification first
- keep subcategory, risk flags, and India state focus as structured metadata
- use context output for transparency and later routing only

Why top-level first:
- we do not yet have enough clean labeled data for all subcategories
- top-level domains are stable enough to train before routing becomes model-led

Output schema:
- `domain`
- `subcategory`
- `confidence`
- `decision_source`
- `risk_flags`
- `state_focus`
- `taxonomy_version`

Next steps after this scaffold:
1. build `data/context/v1`
2. train `checkpoints/context/latest`
3. integrate trained context behind feature flag
4. use context in retrieval/source routing
5. benchmark impact on evidence quality
