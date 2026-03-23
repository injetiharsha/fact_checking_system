# Stance Stage 2 Hardcases v3 Bias Refresh

This dataset merges the existing `stage2_hardcases_v2` set with the new support-bias residual packet.

Builder:
- training/common/build_stance_stage2_hardcases_v3_bias.py

Inputs:
- data/stance/stage2_hardcases_v2/
- data/stance/support_bias_v1/support_bias_stance_packet_v1.jsonl

Output:
- data/stance/stage2_hardcases_v3_bias/

Training config:
- training/configs/stance_stage2_hardcases_v3_bias.yaml

Build command:

```powershell
.\.venv\Scripts\python.exe training\common\build_stance_stage2_hardcases_v3_bias.py
```

Train command:

```powershell
.\.venv\Scripts\python.exe training\stance\train.py --config training\configs\stance_stage2_hardcases_v3_bias.yaml
```

Purpose:
- preserve the original two-stage stance training path
- add support-bias residuals into a broader stage-2 refresh
- avoid overfitting to the tiny 12-row packet alone
