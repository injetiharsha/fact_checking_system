import argparse
import os
from pathlib import Path

import yaml


def build_config(base_config: str, use_drive: bool, drive_dir: str) -> Path:
    base_path = Path(base_config)
    if not base_path.exists():
        raise FileNotFoundError(f"Base config not found: {base_path}")

    colab_path = base_path.with_name(base_path.stem + "_colab.yaml")

    with base_path.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    if use_drive:
        run_name = Path(cfg["output"]["checkpoint_dir"]).name
        os.makedirs(drive_dir, exist_ok=True)
        cfg["output"]["checkpoint_dir"] = os.path.join(drive_dir, "checkpoints/relevance", run_name)
        cfg["output"]["metrics_dir"] = os.path.join(drive_dir, "training_artifacts/relevance", run_name)
    else:
        run_name = Path(cfg["output"]["checkpoint_dir"]).name
        cfg["output"]["metrics_dir"] = os.path.join("training_artifacts/relevance", run_name)

    cfg["training"]["batch_size"] = 16
    cfg["training"]["eval_batch_size"] = 16
    cfg["training"]["max_length"] = 256
    cfg["training"]["logging_steps"] = 20
    cfg["training"]["save_total_limit"] = 2

    with colab_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, sort_keys=False)

    return colab_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a Colab-friendly relevance config.")
    parser.add_argument("--base-config", required=True)
    parser.add_argument("--use-drive", default=os.getenv("USE_DRIVE", "1"))
    parser.add_argument(
        "--drive-dir",
        default=os.getenv("DRIVE_DIR", "/content/drive/MyDrive/fact_checking_system_colab"),
    )
    args = parser.parse_args()

    use_drive = str(args.use_drive).strip().lower() in {"1", "true", "yes", "on"}
    out_path = build_config(
        base_config=args.base_config,
        use_drive=use_drive,
        drive_dir=args.drive_dir,
    )
    print(out_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
