import argparse
import json
from pathlib import Path


def build_outputs(source_path: Path):
    data = json.loads(source_path.read_text(encoding='utf-8'))

    benchmark_rows = [
        {
            'claim': row['claim'],
            'expected_verdict': row['expected_verdict'],
        }
        for row in data
        if row.get('expected_checkability') == 'checkable' and row.get('expected_verdict')
    ]

    checkability_rows = [
        {
            'text': row['claim'],
            'group': row.get('category', 'mixed'),
            'expected_label': row['expected_checkability'],
            'expected_subtype': row.get(
                'expected_subtype',
                'factual_claim' if row.get('expected_checkability') == 'checkable' else 'other_uncheckable',
            ),
        }
        for row in data
    ]

    benchmark_path = source_path.with_name(source_path.stem + '_benchmark.json')
    checkability_path = source_path.with_name(source_path.stem + '_checkability.json')

    benchmark_path.write_text(json.dumps(benchmark_rows, ensure_ascii=False, indent=2), encoding='utf-8')
    checkability_path.write_text(json.dumps(checkability_rows, ensure_ascii=False, indent=2), encoding='utf-8')

    print(f'benchmark_rows={len(benchmark_rows)} path={benchmark_path}')
    print(f'checkability_rows={len(checkability_rows)} path={checkability_path}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Build UTF-8-safe derived files from a mixed claim seed.')
    parser.add_argument('--source', default='benchmark_claims/claim_seed_100_mixed_v1.json')
    args = parser.parse_args()
    build_outputs(Path(args.source))
