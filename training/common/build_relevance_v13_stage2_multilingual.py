import argparse
import json
import random
import re
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

import sys
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from training.common.utils import ensure_dir, stratified_split_records

SEED = 42


def read_jsonl(path):
    rows = []
    file_path = Path(path)
    if not file_path.exists():
        return rows
    with file_path.open('r', encoding='utf-8-sig') as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def normalize_record(row, idx_prefix, idx):
    out = {
        'id': row.get('id') or f'{idx_prefix}_{idx}',
        'claim': row['claim'],
        'candidate_sentence': row['candidate_sentence'],
        'label': int(row['label']),
        'source': row.get('source', idx_prefix),
        'source_url': row.get('source_url'),
        'selection_origin': row.get('selection_origin', idx_prefix),
    }
    if 'language' in row:
        out['language'] = row['language']
    return out


def load_records():
    records = []
    for idx, row in enumerate(read_jsonl('data/relevance/v13_broad/dataset.jsonl'), start=1):
        records.append(normalize_record(row, 'relevance_v13_stage1', idx))

    offset = len(records)
    seed_paths = [
        'data/relevance/seeds/india_multilingual_native_v13.jsonl',
        'data/relevance/seeds/india_multilingual_native_v13_generated.jsonl',
    ]
    running = offset
    for seed_path in seed_paths:
        source_prefix = Path(seed_path).stem
        for idx, row in enumerate(read_jsonl(seed_path), start=1):
            records.append(normalize_record(row, source_prefix, running + idx))
        running = len(records)
    return records


def norm_text(value):
    text = unicodedata.normalize('NFKC', str(value))
    text = re.sub(r'\s+', ' ', text).strip()
    return text.casefold()


def dedupe(records):
    seen = set()
    out = []
    for row in records:
        key = (
            norm_text(row['claim']),
            norm_text(row['candidate_sentence']),
            int(row['label']),
            row.get('language') or '',
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def main():
    parser = argparse.ArgumentParser(description='Build stage-2 multilingual relevance dataset.')
    parser.add_argument('--output-dir', default='data/relevance/v13_stage2_multilingual')
    args = parser.parse_args()

    records = dedupe(load_records())
    output_dir = ensure_dir(args.output_dir)
    train_rows, val_rows, test_rows = stratified_split_records(records, label_key='label', validation_ratio=0.15, test_ratio=0.15, seed=SEED)

    for file_name, rows in (
        ('train.jsonl', train_rows),
        ('validation.jsonl', val_rows),
        ('test.jsonl', test_rows),
        ('dataset.jsonl', records),
    ):
        output_path = output_dir / file_name
        with output_path.open('w', encoding='utf-8') as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + '\n')

    source_counts = Counter(row.get('source', 'unknown') for row in records)
    language_counts = Counter(row.get('language') for row in records if row.get('language'))
    metadata = {
        'dataset_name': 'relevance_v13_stage2_multilingual',
        'record_count': len(records),
        'train_count': len(train_rows),
        'validation_count': len(val_rows),
        'test_count': len(test_rows),
        'native_multilingual_records': sum(1 for row in records if str(row.get('source', '')).startswith('india_multilingual_native_v13')),
        'languages': sorted(language_counts.keys()),
        'language_counts': dict(sorted(language_counts.items())),
        'source_counts': dict(sorted(source_counts.items())),
    }
    with (output_dir / 'metadata.json').open('w', encoding='utf-8') as handle:
        json.dump(metadata, handle, ensure_ascii=False, indent=2)

    print(f"Wrote {len(train_rows)} train, {len(val_rows)} validation, and {len(test_rows)} test records to {output_dir}")
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
