$ErrorActionPreference = "Continue"
Set-Location "F:\fact_checking_system"
if (!(Test-Path "logs\training")) { New-Item -ItemType Directory -Path "logs\training" | Out-Null }
Add-Content -Path "logs\training\stance_stage1_combined.log" -Value ("[runner] starting " + (Get-Date).ToString("o"))
$env:HF_HUB_OFFLINE = "1"
$env:TRANSFORMERS_OFFLINE = "1"
$env:HF_DATASETS_OFFLINE = "1"
$env:PYTHONWARNINGS = "ignore"
& .\.venv\Scripts\python.exe -u training\stance\train.py --config training\configs\stance_stage1_public.yaml 2>&1 | Tee-Object -FilePath logs\training\stance_stage1_combined.log -Append
Add-Content -Path "logs\training\stance_stage1_combined.log" -Value ("[runner] finished " + (Get-Date).ToString("o"))
