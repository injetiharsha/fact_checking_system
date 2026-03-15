import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from datasets import Dataset, DatasetDict
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    EarlyStoppingCallback,
    Trainer,
    TrainingArguments,
)

from training.common.config import load_yaml_config
from training.common.metrics import classification_metrics, save_run_metrics
from training.common.utils import set_seed


def _read_jsonl(path: str) -> list[dict]:
    rows = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _load_local_dataset(config: dict) -> DatasetDict:
    files = {
        "train": config["data"]["train_file"],
        "validation": config["data"]["validation_file"],
    }
    if config["data"].get("test_file"):
        files["test"] = config["data"]["test_file"]

    dataset_map = {}
    for split_name, file_path in files.items():
        dataset_map[split_name] = Dataset.from_list(_read_jsonl(file_path))
    return DatasetDict(dataset_map)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train relevance reranker.")
    parser.add_argument("--config", default="training/configs/relevance.yaml")
    args = parser.parse_args()
    config = load_yaml_config(args.config)
    set_seed(int(config.get("seed", 42)))
    model_candidates = [config["model"]["name"], *config["model"].get("fallback_models", [])]

    dataset = _load_local_dataset(config)
    model_name = None
    tokenizer = None
    model = None
    last_exc = None
    for candidate in model_candidates:
        try:
            tokenizer = AutoTokenizer.from_pretrained(candidate, use_fast=False)
            model = AutoModelForSequenceClassification.from_pretrained(
                candidate,
                num_labels=2,
                id2label={0: "IRRELEVANT", 1: "RELEVANT"},
                label2id={"IRRELEVANT": 0, "RELEVANT": 1},
            )
            model_name = candidate
            break
        except Exception as exc:
            last_exc = exc
    if model is None or tokenizer is None:
        raise RuntimeError(f"Unable to load any configured relevance model: {last_exc}")

    def preprocess(batch):
        tokens = tokenizer(
            batch["claim"],
            batch["candidate_sentence"],
            truncation=True,
            max_length=int(config["training"].get("max_length", 256)),
        )
        tokens["labels"] = batch["label"]
        return tokens

    encoded = dataset.map(
        preprocess,
        batched=True,
        remove_columns=dataset["train"].column_names,
    )
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
        load_best_model_at_end=True,
        metric_for_best_model="accuracy",
        report_to=[],
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
            )
        ],
    )
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
    save_run_metrics(config["output"]["metrics_dir"], "relevance", metrics, payload)


if __name__ == "__main__":
    main()
