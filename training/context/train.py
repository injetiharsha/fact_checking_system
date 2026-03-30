import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from datasets import Dataset, DatasetDict
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    EarlyStoppingCallback,
    Trainer,
    TrainerCallback,
    TrainingArguments,
)

from training.common.config import load_yaml_config
from training.common.metrics import classification_metrics, save_run_metrics
from training.common.utils import ensure_dir, set_seed


LABELS = [
    "science",
    "health",
    "technology",
    "history",
    "politics_government",
    "economics_business",
    "geography",
    "space_astronomy",
    "environment_climate",
    "society_culture",
    "law_crime",
    "sports",
    "entertainment",
    "general_factual",
]
LABEL2ID = {label: idx for idx, label in enumerate(LABELS)}


class ProgressWriter:
    def __init__(self, metrics_dir: str | Path):
        self.metrics_dir = ensure_dir(metrics_dir)
        self.status_path = self.metrics_dir / 'live_status.json'
        self.log_path = self.metrics_dir / 'live_progress.log'

    def update(self, stage: str, **extra):
        payload = {
            'timestamp_utc': datetime.now(timezone.utc).isoformat(),
            'stage': stage,
            **extra,
        }
        self.status_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        with self.log_path.open('a', encoding='utf-8') as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + '\n')


class ConsoleProgressCallback(TrainerCallback):
    def __init__(self, progress: ProgressWriter):
        self.progress = progress

    def on_train_begin(self, args, state, control, **kwargs):
        message = f"Training started: epochs={args.num_train_epochs}, batch_size={args.per_device_train_batch_size}"
        print(message, flush=True)
        self.progress.update('train_begin', epochs=args.num_train_epochs, batch_size=args.per_device_train_batch_size)

    def on_epoch_begin(self, args, state, control, **kwargs):
        next_epoch = int(state.epoch or 0) + 1
        print(f"\nEpoch {next_epoch} starting...", flush=True)
        self.progress.update('epoch_begin', epoch=next_epoch, global_step=state.global_step)

    def on_log(self, args, state, control, logs=None, **kwargs):
        if logs:
            print(f"Log step {state.global_step}: {logs}", flush=True)
            self.progress.update('log', global_step=state.global_step, logs=logs)

    def on_evaluate(self, args, state, control, metrics=None, **kwargs):
        print(f"Evaluation after step {state.global_step}: {metrics}", flush=True)
        self.progress.update('evaluate', global_step=state.global_step, metrics=metrics or {})

    def on_save(self, args, state, control, **kwargs):
        print(f"Checkpoint saved at step {state.global_step} -> {args.output_dir}", flush=True)
        self.progress.update('save', global_step=state.global_step, output_dir=args.output_dir)

    def on_train_end(self, args, state, control, **kwargs):
        print('Training finished.', flush=True)
        self.progress.update('train_end', global_step=state.global_step)


def load_model_and_tokenizer(model_candidates, progress: ProgressWriter):
    last_exc = None
    for model_name in model_candidates:
        try:
            progress.update('loading_model', candidate=model_name)
            tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=False)
            model = AutoModelForSequenceClassification.from_pretrained(
                model_name,
                num_labels=len(LABELS),
                id2label={idx: label.upper() for label, idx in LABEL2ID.items()},
                label2id={label.upper(): idx for label, idx in LABEL2ID.items()},
            )
            progress.update('model_loaded', model_name=model_name)
            return model_name, tokenizer, model
        except Exception as exc:
            last_exc = exc
            print(f"Failed to load {model_name}: {exc}", flush=True)
            progress.update('model_load_failed', candidate=model_name, error=str(exc))
    raise RuntimeError(f"Unable to load any configured context model: {last_exc}")


def _read_jsonl(path: Path):
    rows = []
    with path.open('r', encoding='utf-8') as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _load_local_dataset(config):
    data_files = {
        'train': Path(config['data']['train_file']),
        'validation': Path(config['data']['validation_file']),
    }
    if config['data'].get('test_file'):
        data_files['test'] = Path(config['data']['test_file'])

    dataset_map = {}
    for split, file_path in data_files.items():
        rows = _read_jsonl(file_path)
        dataset_map[split] = Dataset.from_list(rows)
    return DatasetDict(dataset_map)


def main() -> None:
    parser = argparse.ArgumentParser(description='Train context classifier.')
    parser.add_argument('--config', default='training/configs/context.yaml')
    args = parser.parse_args()
    config = load_yaml_config(args.config)
    progress = ProgressWriter(config['output']['metrics_dir'])
    progress.update('startup', config=args.config)

    set_seed(int(config.get('seed', 42)))
    model_candidates = [config['model']['name'], *config['model'].get('fallback_models', [])]

    print(f"Loading context training config: {args.config}", flush=True)
    print(f"Model candidates: {model_candidates}", flush=True)
    print(f"CUDA available: {torch.cuda.is_available()}", flush=True)
    progress.update('environment', cuda_available=torch.cuda.is_available())
    if torch.cuda.is_available():
        device_name = torch.cuda.get_device_name(0)
        print(f"CUDA device: {device_name}", flush=True)
        progress.update('environment', cuda_available=True, cuda_device=device_name)

    print('Loading dataset files...', flush=True)
    progress.update('loading_dataset')
    dataset = _load_local_dataset(config)
    split_sizes = {split: len(dataset[split]) for split in dataset.keys()}
    print(split_sizes, flush=True)
    progress.update('dataset_loaded', splits=split_sizes)

    print('Loading tokenizer/model...', flush=True)
    model_name, tokenizer, model = load_model_and_tokenizer(model_candidates, progress)
    print(f"Using model: {model_name}", flush=True)

    def preprocess(batch):
        tokens = tokenizer(
            batch['text'],
            truncation=True,
            max_length=int(config['training'].get('max_length', 128)),
        )
        tokens['labels'] = [LABEL2ID[label] for label in batch['label']]
        return tokens

    print('Tokenizing dataset...', flush=True)
    progress.update('tokenizing_dataset')
    encoded = dataset.map(
        preprocess,
        batched=True,
        remove_columns=dataset['train'].column_names,
    )

    print('Preparing trainer...', flush=True)
    progress.update('preparing_trainer')
    training_args = TrainingArguments(
        output_dir=config['output']['checkpoint_dir'],
        per_device_train_batch_size=int(config['training'].get('batch_size', 8)),
        per_device_eval_batch_size=int(config['training'].get('eval_batch_size', 8)),
        learning_rate=float(config['training'].get('learning_rate', 2e-5)),
        num_train_epochs=float(config['training'].get('epochs', 12)),
        evaluation_strategy='epoch',
        save_strategy='epoch',
        save_total_limit=int(config['training'].get('save_total_limit', 2)),
        logging_steps=int(config['training'].get('logging_steps', 10)),
        logging_strategy='steps',
        load_best_model_at_end=True,
        metric_for_best_model='accuracy',
        report_to=[],
        disable_tqdm=False,
    )

    def compute_metrics(eval_pred):
        logits, labels = eval_pred
        predictions = logits.argmax(axis=-1)
        return classification_metrics(labels, predictions)

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=encoded['train'],
        eval_dataset=encoded['validation'],
        tokenizer=tokenizer,
        compute_metrics=compute_metrics,
        callbacks=[
            EarlyStoppingCallback(
                early_stopping_patience=int(config['training'].get('early_stopping_patience', 5))
            ),
            ConsoleProgressCallback(progress),
        ],
    )

    print('Starting trainer.train()...', flush=True)
    progress.update('training_call_start')
    trainer.train()

    print('Running final validation...', flush=True)
    progress.update('final_validation')
    metrics = trainer.evaluate()
    test_metrics = None
    if 'test' in encoded:
        print('Running held-out test evaluation...', flush=True)
        progress.update('test_evaluation')
        trainer.pop_callback(EarlyStoppingCallback)
        test_metrics = trainer.evaluate(eval_dataset=encoded['test'], metric_key_prefix='test')

    print(f"Saving model to {config['output']['checkpoint_dir']}...", flush=True)
    progress.update('saving_model', output_dir=config['output']['checkpoint_dir'])
    trainer.save_model(config['output']['checkpoint_dir'])
    payload = {
        'checkpoint_path': config['output']['checkpoint_dir'],
        'model_name': model_name,
        'validation_file': config['data']['validation_file'],
        'labels': LABELS,
    }
    if config['data'].get('test_file'):
        payload['test_file'] = config['data']['test_file']
    if test_metrics:
        payload['test_metrics'] = test_metrics
    save_run_metrics(config['output']['metrics_dir'], 'context', metrics, payload)
    progress.update('completed', metrics=metrics, test_metrics=test_metrics or {})
    print(f"Saved metrics to {config['output']['metrics_dir']}", flush=True)


if __name__ == '__main__':
    main()
