# Support Bias Stance Fine-Tune

This is the narrow training path for the support-bias residual packet.

Files:
- data/stance/support_bias_v1/support_bias_stance_packet_v1.jsonl
- data/stance/support_bias_v1_split/train.jsonl
- data/stance/support_bias_v1_split/validation.jsonl
- data/stance/support_bias_v1_split/test.jsonl
- training/configs/stance_support_bias_v1.yaml

Train command:

```powershell
.\.venv\Scripts\python.exe training\stance\train.py --config training\configs\stance_support_bias_v1.yaml
```

Notes:
- this is a tiny residual packet, so treat it as a calibration experiment, not a full standalone stance model
- best use is either:
  - quick residual fine-tune from `stage1_public_small`, or
  - merge later into a broader stage-2 residual dataset
- because the packet is very small, overfitting risk is high
- prefer evaluating on the support-bias packet and the 68-claim benchmark after training
