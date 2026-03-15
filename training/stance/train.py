import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from datasets import Dataset, DatasetDict, disable_progress_bar, load_from_disk
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    EarlyStoppingCallback,
    Trainer,
    TrainerCallback,
    TrainingArguments,
)
from transformers.utils import logging as hf_logging

from training.common.config import load_yaml_config
from training.common.metrics import classification_metrics, save_run_metrics
from training.common.utils import ensure_dir, set_seed


LABELS = ["REFUTE", "NEUTRAL", "SUPPORT"]
LABEL2ID = {label: idx for idx, label in enumerate(LABELS)}


class ProgressWriter:
    def __init__(self, metrics_dir: str | Path):
        self.metrics_dir = ensure_dir(metrics_dir)
        self.status_path = self.metrics_dir / "live_status.json"
        self.log_path = self.metrics_dir / "live_progress.log"

    def update(self, stage: str, **extra):
        payload = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "stage": stage,
            **extra,
        }
        self.status_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


class ConsoleProgressCallback(TrainerCallback):
    def __init__(self, progress: ProgressWriter):
        self.progress = progress

    def on_train_begin(self, args, state, control, **kwargs):
        print(f"Training started: epochs={args.num_train_epochs}, batch_size={args.per_device_train_batch_size}", flush=True)
        self.progress.update("train_begin", epochs=args.num_train_epochs, batch_size=args.per_device_train_batch_size)

    def on_epoch_begin(self, args, state, control, **kwargs):
        next_epoch = int(state.epoch or 0) + 1
        print(f"Epoch {next_epoch} starting...", flush=True)
        self.progress.update("epoch_begin", epoch=next_epoch, global_step=state.global_step)

    def on_log(self, args, state, control, logs=None, **kwargs):
        if logs:
            print(f"Log step {state.global_step}: {logs}", flush=True)
            self.progress.update("log", global_step=state.global_step, logs=logs)

    def on_evaluate(self, args, state, control, metrics=None, **kwargs):
        print(f"Evaluation after step {state.global_step}: {metrics}", flush=True)
        self.progress.update("evaluate", global_step=state.global_step, metrics=metrics or {})

    def on_save(self, args, state, control, **kwargs):
        print(f"Checkpoint saved at step {state.global_step} -> {args.output_dir}", flush=True)
        self.progress.update("save", global_step=state.global_step, output_dir=args.output_dir)

    def on_train_end(self, args, state, control, **kwargs):
        print("Training finished.", flush=True)
        self.progress.update("train_end", global_step=state.global_step)


def load_model_and_tokenizer(model_candidates, progress: ProgressWriter):
    last_exc = None
    for model_name in model_candidates:
        try:
            progress.update("loading_model", candidate=model_name)
            tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=False)
            model = AutoModelForSequenceClassification.from_pretrained(
                model_name,
                num_labels=len(LABELS),
                id2label={idx: label for label, idx in LABEL2ID.items()},
                label2id=LABEL2ID,
            )
            progress.update("model_loaded", model_name=model_name)
            return model_name, tokenizer, model
        except Exception as exc:
            last_exc = exc
            print(f"Failed to load {model_name}: {exc}", flush=True)
            progress.update("model_load_failed", candidate=model_name, error=str(exc))
    raise RuntimeError(f"Unable to load any configured stance model: {last_exc}")


def _read_jsonl(path: Path, split_name: str, progress: ProgressWriter | None = None):
    rows = []
    print(f"Reading {split_name} from {path}...", flush=True)
    if progress is not None:
        progress.update("reading_split", split=split_name, path=str(path))
    with path.open("r", encoding="utf-8") as handle:
        for idx, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
            if idx % 100000 == 0:
                print(f"Loaded {split_name}: {idx} lines", flush=True)
                if progress is not None:
                    progress.update("reading_split_progress", split=split_name, lines=idx)
    print(f"Finished {split_name}: {len(rows)} rows", flush=True)
    if progress is not None:
        progress.update("split_loaded", split=split_name, rows=len(rows))
    return rows


def _load_local_dataset(config, progress: ProgressWriter | None = None):
    data_files = {
        "train": Path(config["data"]["train_file"]),
        "validation": Path(config["data"]["validation_file"]),
    }
    if config["data"].get("test_file"):
        data_files["test"] = Path(config["data"]["test_file"])

    dataset_map = {}
    for split, file_path in data_files.items():
        rows = _read_jsonl(file_path, split, progress)
        dataset_map[split] = Dataset.from_list(rows)
    return DatasetDict(dataset_map)


def _tokenized_cache_dir(config) -> Path | None:
    cache_dir = config.get("data", {}).get("tokenized_cache_dir")
    if not cache_dir:
        return None
    return Path(cache_dir)


def _load_or_build_encoded_dataset(config, dataset, tokenizer, progress: ProgressWriter):
    cache_dir = _tokenized_cache_dir(config)
    if cache_dir and cache_dir.exists():
        print(f"Loading tokenized dataset cache from {cache_dir}...", flush=True)
        progress.update("loading_tokenized_cache", path=str(cache_dir))
        encoded = load_from_disk(str(cache_dir))
        progress.update("tokenized_cache_loaded", path=str(cache_dir))
        return encoded

    def preprocess(batch):
        tokens = tokenizer(
            batch["claim"],
            batch["evidence"],
            truncation=True,
            max_length=int(config["training"].get("max_length", 256)),
            verbose=False,
        )
        tokens["labels"] = [LABEL2ID[label] for label in batch["label"]]
        return tokens

    print("Tokenizing dataset...", flush=True)
    progress.update("tokenizing_dataset")
    disable_progress_bar()
    hf_logging.set_verbosity_error()

    encoded_map = {}
    for split_name in dataset.keys():
        print(f"Tokenizing split: {split_name} ({len(dataset[split_name])} rows)", flush=True)
        progress.update("tokenizing_split", split=split_name, rows=len(dataset[split_name]))
        encoded_map[split_name] = dataset[split_name].map(
            preprocess,
            batched=True,
            remove_columns=dataset[split_name].column_names,
        )
        print(f"Finished tokenizing split: {split_name}", flush=True)
        progress.update("tokenized_split", split=split_name, rows=len(encoded_map[split_name]))
    encoded = DatasetDict(encoded_map)

    if cache_dir:
        ensure_dir(cache_dir.parent)
        print(f"Saving tokenized dataset cache to {cache_dir}...", flush=True)
        progress.update("saving_tokenized_cache", path=str(cache_dir))
        encoded.save_to_disk(str(cache_dir))
        progress.update("tokenized_cache_saved", path=str(cache_dir))
    return encoded


def main() -> None:
    parser = argparse.ArgumentParser(description="Train stance/NLI classifier.")
    parser.add_argument("--config", default="training/configs/stance.yaml")
    args = parser.parse_args()
    config = load_yaml_config(args.config)
    progress = ProgressWriter(config["output"]["metrics_dir"])
    progress.update("startup", config=args.config)

    set_seed(int(config.get("seed", 42)))
    model_candidates = [config["model"]["name"], *config["model"].get("fallback_models", [])]

    print(f"Loading stance training config: {args.config}", flush=True)
    print(f"Model candidates: {model_candidates}", flush=True)
    print(f"CUDA available: {torch.cuda.is_available()}", flush=True)
    progress.update("environment", cuda_available=torch.cuda.is_available())
    if torch.cuda.is_available():
        device_name = torch.cuda.get_device_name(0)
        print(f"CUDA device: {device_name}", flush=True)
        progress.update("environment", cuda_available=True, cuda_device=device_name)

    print("Loading dataset files...", flush=True)
    progress.update("loading_dataset")
    dataset = _load_local_dataset(config, progress)
    split_sizes = {split: len(dataset[split]) for split in dataset.keys()}
    print(split_sizes, flush=True)
    progress.update("dataset_loaded", splits=split_sizes)

    print("Loading tokenizer/model...", flush=True)
    model_name, tokenizer, model = load_model_and_tokenizer(model_candidates, progress)
    print(f"Using model: {model_name}", flush=True)

    encoded = _load_or_build_encoded_dataset(config, dataset, tokenizer, progress)

    print("Preparing trainer...", flush=True)
    progress.update("preparing_trainer")
    training_args = TrainingArguments(
        output_dir=config["output"]["checkpoint_dir"],
        per_device_train_batch_size=int(config["training"].get("batch_size", 8)),
        per_device_eval_batch_size=int(config["training"].get("eval_batch_size", 8)),
        learning_rate=float(config["training"].get("learning_rate", 2e-5)),
        num_train_epochs=float(config["training"].get("epochs", 3)),
        evaluation_strategy="epoch",
        save_strategy="epoch",
        save_total_limit=int(config["training"].get("save_total_limit", 2)),
        logging_steps=int(config["training"].get("logging_steps", 10)),
        logging_strategy="steps",
        load_best_model_at_end=True,
        metric_for_best_model="accuracy",
        report_to=[],
        disable_tqdm=True,
    )

    def compute_metrics(eval_pred):
        logits, labels = eval_pred
        predictions = logits.argmax(axis=-1)
        return classification_metrics(labels, predictions)

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=encoded["train"],
        eval_dataset=encoded["validation"],
        tokenizer=tokenizer,
        compute_metrics=compute_metrics,
        callbacks=[
            EarlyStoppingCallback(
                early_stopping_patience=int(
                    config["training"].get("early_stopping_patience", 5)
                )
            ),
            ConsoleProgressCallback(progress),
        ],
    )
    progress.update("trainer_ready")
    trainer.train()
    metrics = trainer.evaluate()
    test_metrics = None
    if "test" in encoded:
        trainer.pop_callback(EarlyStoppingCallback)
        test_metrics = trainer.evaluate(eval_dataset=encoded["test"], metric_key_prefix="test")
    trainer.save_model(config["output"]["checkpoint_dir"])
    payload = {
        "checkpoint_path": config["output"]["checkpoint_dir"],
        "model_name": model_name,
        "validation_file": config["data"]["validation_file"],
    }
    if config["data"].get("test_file"):
        payload["test_file"] = config["data"]["test_file"]
    if test_metrics:
        payload["test_metrics"] = test_metrics
    save_run_metrics(config["output"]["metrics_dir"], "stance", metrics, payload)


if __name__ == "__main__":
    main()
