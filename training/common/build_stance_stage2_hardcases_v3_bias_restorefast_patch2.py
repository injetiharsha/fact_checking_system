import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from training.common.utils import ensure_dir, stratified_split_records


def load_jsonl(path: Path):
    rows = []
    if not path.exists():
        return rows
    with path.open('r', encoding='utf-8-sig') as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows):
    with path.open('w', encoding='utf-8-sig') as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + '\n')


def normalize_patch_rows(rows):
    normalized = []
    for idx, row in enumerate(rows, start=1):
        normalized.append({
            'id': row.get('id') or f'restorefast_patch2_{idx}',
            'claim': row['claim'],
            'evidence': row['evidence'],
            'label': row['label'],
            'source': row.get('source') or 'restorefast_patch2',
            'source_weight': float(row.get('source_weight', 1.0)),
            'weak_label': bool(row.get('weak_label', False)),
            'residual_type': row.get('residual_type', 'restorefast_patch2'),
            'notes': row.get('notes'),
        })
    return normalized


def main():
    parser = argparse.ArgumentParser(description='Build stance v3_bias restorefast patch2 dataset.')
    parser.add_argument('--base-dir', default='data/stance/stage2_hardcases_v3_bias_restorefast_patch1')
    parser.add_argument('--patch-file', default='data/stance/residuals/stance_restorefast_patch2_residual.jsonl')
    parser.add_argument('--output-dir', default='data/stance/stage2_hardcases_v3_bias_restorefast_patch2')
    parser.add_argument('--seed', type=int, default=42)
    args = parser.parse_args()

    base_dir = Path(args.base_dir)
    patch_file = Path(args.patch_file)
    output_dir = ensure_dir(args.output_dir)

    base_rows = []
    for split_name in ('train', 'validation', 'test'):
        base_rows.extend(load_jsonl(base_dir / f'{split_name}.jsonl'))

    patch_rows = normalize_patch_rows(load_jsonl(patch_file))

    merged = []
    seen = set()
    for row in base_rows + patch_rows:
        key = (
            row['claim'].strip().casefold(),
            row['evidence'].strip().casefold(),
            row['label'].strip().upper(),
        )
        if key in seen:
            continue
        seen.add(key)
        merged.append(row)

    train_rows, val_rows, test_rows = stratified_split_records(
        merged,
        label_key='label',
        validation_ratio=0.12,
        test_ratio=0.12,
        seed=args.seed,
    )

    write_jsonl(output_dir / 'train.jsonl', train_rows)
    write_jsonl(output_dir / 'validation.jsonl', val_rows)
    write_jsonl(output_dir / 'test.jsonl', test_rows)

    metadata = {
        'total_rows': len(merged),
        'train_rows': len(train_rows),
        'validation_rows': len(val_rows),
        'test_rows': len(test_rows),
        'label_distribution': dict(Counter(row['label'] for row in merged)),
        'sources': dict(Counter(row.get('source', 'unknown') for row in merged)),
        'base_dir': str(base_dir),
        'patch_file': str(patch_file),
        'patch_rows_added': len(patch_rows),
    }
    (output_dir / 'metadata.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8-sig')
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
