from app.decision.rules import hard_fact_check
from app.decision.structure import validate_claim

def final_verdict(ml_label, ml_confidence, evidence_scores, claim):
    # 1. Structural validation
    structural, reason = validate_claim(claim)
    if structural:
        return {
            "final_verdict": structural,
            "reason": reason
        }

    # 2. Hard rules
    rule_result, rule_reason = hard_fact_check(claim)
    if rule_result:
        return {
            "final_verdict": rule_result,
            "reason": rule_reason
        }

    # 3. Evidence-based decision
    if evidence_scores:
        avg_similarity = sum(evidence_scores) / len(evidence_scores)

        if avg_similarity >= 0.6:
            return {
                "final_verdict": "REAL",
                "reason": "Strong external evidence"
            }

        if avg_similarity <= 0.4:
            return {
                "final_verdict": "FAKE",
                "reason": "Evidence contradicts claim"
            }

    # 4. ML confidence fallback
    if ml_confidence >= 0.85:
        return {
            "final_verdict": ml_label,
            "reason": "High ML confidence, limited evidence"
        }

    # 5. Final fallback
    return {
        "final_verdict": "UNCERTAIN",
        "reason": "Insufficient evidence"
    }
