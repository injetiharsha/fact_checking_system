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
    with path.open('r', encoding='utf-8') as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows):
    with path.open('w', encoding='utf-8') as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + '\n')


def main():
    parser = argparse.ArgumentParser(description='Build merged stance hardcases dataset with support-bias residuals.')
    parser.add_argument('--base-dir', default='data/stance/stage2_hardcases_v2')
    parser.add_argument('--bias-file', default='data/stance/support_bias_v1/support_bias_stance_packet_v1.jsonl')
    parser.add_argument('--output-dir', default='data/stance/stage2_hardcases_v3_bias')
    args = parser.parse_args()

    base_dir = Path(args.base_dir)
    bias_file = Path(args.bias_file)
    output_dir = ensure_dir(args.output_dir)

    base_rows = []
    for split_name in ('train', 'validation', 'test'):
        base_rows.extend(load_jsonl(base_dir / f'{split_name}.jsonl'))

    bias_rows = load_jsonl(bias_file)
    normalized_bias = []
    for idx, row in enumerate(bias_rows, start=1):
        normalized_bias.append({
            'id': row.get('id') or f'support_bias_v1_{idx}',
            'claim': row['claim'],
            'evidence': row['evidence'],
            'label': row['label'],
            'source': f"support_bias:{row.get('source', 'v1')}",
            'source_weight': 1.0,
            'weak_label': False,
            'residual_type': row.get('type'),
        })

    merged = []
    seen = set()
    for row in base_rows + normalized_bias:
        key = (row['claim'].strip().casefold(), row['evidence'].strip().casefold(), row['label'].strip().upper())
        if key in seen:
            continue
        seen.add(key)
        merged.append(row)

    train_rows, val_rows, test_rows = stratified_split_records(
        merged,
        label_key='label',
        validation_ratio=0.12,
        test_ratio=0.12,
        seed=42,
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
        'bias_file': str(bias_file),
        'bias_rows_added': len(normalized_bias),
    }
    (output_dir / 'metadata.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
