@echo off
cd /d F:\fact_checking_system
if not exist logs\training mkdir logs\training
echo [runner] starting %date% %time%>> logs\training\stance_stage2_cmd.log
set HF_HUB_OFFLINE=1
set TRANSFORMERS_OFFLINE=1
set HF_DATASETS_OFFLINE=1
set PYTHONWARNINGS=ignore
.\.venv\Scripts\python.exe -u training\stance\train.py --config training\configs\stance_stage2_hardcases.yaml >> logs\training\stance_stage2_cmd.log 2>&1
echo [runner] finished %date% %time%>> logs\training\stance_stage2_cmd.log
