import argparse
import os
from pathlib import Path

import yaml


def build_configs(use_drive: bool, drive_dir: str) -> tuple[Path, Path]:
    base_stage1 = Path("training/configs/stance_stage1_public_small.yaml")
    base_stage2 = Path("training/configs/stance_stage2_hardcases_v2.yaml")
    colab_stage1 = Path("training/configs/stance_stage1_public_small_colab.yaml")
    colab_stage2 = Path("training/configs/stance_stage2_hardcases_v2_colab.yaml")

    with base_stage1.open("r", encoding="utf-8") as f:
        s1 = yaml.safe_load(f)
    with base_stage2.open("r", encoding="utf-8") as f:
        s2 = yaml.safe_load(f)

    if use_drive:
        os.makedirs(drive_dir, exist_ok=True)
        s1["data"]["tokenized_cache_dir"] = os.path.join(drive_dir, "training_artifacts/stance/stage1_public_small/tokenized_dataset")
        s1["output"]["checkpoint_dir"] = os.path.join(drive_dir, "checkpoints/stance/stage1_public_small")
        s1["output"]["metrics_dir"] = os.path.join(drive_dir, "training_artifacts/stance/stage1_public_small")
        s2["data"]["tokenized_cache_dir"] = os.path.join(drive_dir, "training_artifacts/stance/stage2_hardcases_v2/tokenized_dataset")
        s2["output"]["checkpoint_dir"] = os.path.join(drive_dir, "checkpoints/stance/stage2_hardcases_v2")
        s2["output"]["metrics_dir"] = os.path.join(drive_dir, "training_artifacts/stance/stage2_hardcases_v2")
        s2["model"]["name"] = os.path.join(drive_dir, "checkpoints/stance/stage1_public_small")
    else:
        s1["data"]["tokenized_cache_dir"] = "training_artifacts/stance/stage1_public_small/tokenized_dataset"
        s2["data"]["tokenized_cache_dir"] = "training_artifacts/stance/stage2_hardcases_v2/tokenized_dataset"

    s1["training"]["batch_size"] = 48
    s1["training"]["eval_batch_size"] = 48
    s1["training"]["fp16"] = True
    s1["training"]["max_length"] = 256
    s1["training"]["logging_steps"] = 100
    s1["training"]["save_strategy"] = "steps"
    s1["training"]["save_steps"] = 2000
    s1["training"]["evaluation_strategy"] = "steps"
    s1["training"]["eval_steps"] = 2000
    s1["training"]["save_total_limit"] = 4
    s1["training"]["disable_tqdm"] = True

    s2["training"]["batch_size"] = 48
    s2["training"]["eval_batch_size"] = 48
    s2["training"]["fp16"] = True
    s2["training"]["max_length"] = 256
    s2["training"]["logging_steps"] = 20
    s2["training"]["save_strategy"] = "steps"
    s2["training"]["save_steps"] = 50
    s2["training"]["evaluation_strategy"] = "steps"
    s2["training"]["eval_steps"] = 50
    s2["training"]["save_total_limit"] = 4
    s2["training"]["disable_tqdm"] = True

    with colab_stage1.open("w", encoding="utf-8") as f:
        yaml.safe_dump(s1, f, sort_keys=False)
    with colab_stage2.open("w", encoding="utf-8") as f:
        yaml.safe_dump(s2, f, sort_keys=False)

    return colab_stage1, colab_stage2


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Colab stance-training configs.")
    parser.add_argument("--use-drive", default=os.getenv("USE_DRIVE", "1"))
    parser.add_argument("--drive-dir", default=os.getenv("DRIVE_DIR", "/content/drive/MyDrive/fact_checking_system_colab"))
    args = parser.parse_args()

    use_drive = str(args.use_drive).strip().lower() in {"1", "true", "yes", "on"}
    stage1_path, stage2_path = build_configs(use_drive=use_drive, drive_dir=args.drive_dir)
    print(stage1_path.read_text(encoding="utf-8"))
    print("---")
    print(stage2_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
