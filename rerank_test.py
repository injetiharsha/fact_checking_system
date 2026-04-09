# rerank_test.py
"""
Test script to use your stance model (XNLI/IndicXNLI) as a reranker for claim-evidence pairs.
Evaluates reranking quality on a sample batch.
"""
import json
from semantic.stance_model import StanceDetector

# Load a sample batch of claims and evidence (replace with your data source)
# Format: [{"claim": ..., "evidence_list": ["evidence1", "evidence2", ...]}]
with open("rerank_sample.json", "r", encoding="utf-8") as f:
    batch = json.load(f)

stance = StanceDetector()

results = []
for item in batch:
    claim = item["claim"]
    evidence_list = item["evidence_list"]
    scored = []
    for evidence in evidence_list:
        label, confidence = stance.model.predict(claim, evidence)
        label = (label or "NEUTRAL").upper()
        scored.append({
            "evidence": evidence,
            "label": label,
            "confidence": confidence
        })
    # Rerank: SUPPORT/REFUTE by confidence, NEUTRAL last
    reranked = sorted(
        scored,
        key=lambda x: (x["label"] in ("SUPPORT", "REFUTE"), x["confidence"]),
        reverse=True
    )
    results.append({
        "claim": claim,
        "reranked_evidence": reranked
    })

# Output reranked results
with open("rerank_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print("Reranking complete. Results saved to rerank_results.json.")
