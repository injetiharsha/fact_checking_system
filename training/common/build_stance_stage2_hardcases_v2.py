import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from training.common.augment_stance_with_hardcases import HARD_CASES
from training.common.hardcases_v2 import ADDITIONAL_HARD_CASES
from training.common.utils import ensure_dir, stratified_split_records


def _write_jsonl(path: Path, rows) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build stage-2 hardcase v2 stance dataset.")
    parser.add_argument("--output-dir", default="data/stance/stage2_hardcases_v2")
    args = parser.parse_args()

    seed_rows = list(HARD_CASES) + list(ADDITIONAL_HARD_CASES)
    rows = []
    seen = set()
    for index, row in enumerate(seed_rows, start=1):
        key = (row['claim'].strip().lower(), row['evidence'].strip().lower(), row['label'].strip().upper())
        if key in seen:
            continue
        seen.add(key)
        rows.append({
            'id': f'hardcase_v2_{index}',
            'claim': row['claim'],
            'evidence': row['evidence'],
            'label': row['label'].strip().upper(),
            'source': 'local:hardcase_seed_v2',
            'source_weight': 1.0,
            'weak_label': False,
        })

    train_rows, validation_rows, test_rows = stratified_split_records(rows, label_key='label', validation_ratio=0.12, test_ratio=0.12, seed=42)
    output_dir = ensure_dir(args.output_dir)
    _write_jsonl(output_dir / 'train.jsonl', train_rows)
    _write_jsonl(output_dir / 'validation.jsonl', validation_rows)
    _write_jsonl(output_dir / 'test.jsonl', test_rows)
    metadata = {
        'train_rows': len(train_rows),
        'validation_rows': len(validation_rows),
        'test_rows': len(test_rows),
        'total_rows': len(rows),
        'sources': ['augment_stance_with_hardcases.HARD_CASES', 'hardcases_v2.ADDITIONAL_HARD_CASES'],
    }
    (output_dir / 'metadata.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    print(json.dumps(metadata, indent=2))


if __name__ == '__main__':
    main()
