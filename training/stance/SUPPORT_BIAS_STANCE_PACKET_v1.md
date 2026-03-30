# Support Bias Stance Packet v1

This packet captures real claim-evidence-label triples from the current support-bias residuals.

Files:
- data/stance/support_bias_v1/support_bias_stance_packet_v1.jsonl
- data/stance/support_bias_v1/support_bias_stance_packet_v1.json

Purpose:
- narrow stance residual evaluation
- seed data for a future stance fine-tuning pass
- inspect quoted/reporting, taxonomy, capital mismatch, and comparative mismatch behavior

Label meanings:
- SUPPORT: evidence directly supports the claim
- REFUTE: evidence directly contradicts the claim
- NEUTRAL: evidence is about the topic but should not be taken as direct support or contradiction
