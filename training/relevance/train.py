import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from datasets import load_dataset
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    Trainer,
    TrainingArguments,
)

from training.common.config import load_yaml_config
from training.common.metrics import classification_metrics, save_run_metrics
from training.common.utils import set_seed


def main() -> None:
    parser = argparse.ArgumentParser(description="Train relevance reranker.")
    parser.add_argument("--config", default="training/configs/relevance.yaml")
    args = parser.parse_args()
    config = load_yaml_config(args.config)
    set_seed(int(config.get("seed", 42)))

    dataset = load_dataset("json", data_files={
        "train": str(Path(config["data"]["train_file"])),
        "validation": str(Path(config["data"]["validation_file"])),
    })
    tokenizer = AutoTokenizer.from_pretrained(config["model"]["name"])

    def preprocess(batch):
        tokens = tokenizer(
            batch["claim"],
            batch["candidate_sentence"],
            truncation=True,
            max_length=int(config["training"].get("max_length", 256)),
        )
        tokens["labels"] = batch["label"]
        return tokens

    encoded = dataset.map(preprocess, batched=True)
    model = AutoModelForSequenceClassification.from_pretrained(
        config["model"]["name"],
        num_labels=2,
        id2label={0: "IRRELEVANT", 1: "RELEVANT"},
        label2id={"IRRELEVANT": 0, "RELEVANT": 1},
    )
    training_args = TrainingArguments(
        output_dir=config["output"]["checkpoint_dir"],
        per_device_train_batch_size=int(config["training"].get("batch_size", 8)),
        per_device_eval_batch_size=int(config["training"].get("eval_batch_size", 8)),
        learning_rate=float(config["training"].get("learning_rate", 2e-5)),
        num_train_epochs=float(config["training"].get("epochs", 3)),
        evaluation_strategy="epoch",
        save_strategy="epoch",
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
    )
    trainer.train()
    metrics = trainer.evaluate()
    trainer.save_model(config["output"]["checkpoint_dir"])
    save_run_metrics(config["output"]["metrics_dir"], "relevance", metrics, {
        "checkpoint_path": config["output"]["checkpoint_dir"],
        "validation_file": config["data"]["validation_file"],
    })


if __name__ == "__main__":
    main()
