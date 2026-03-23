import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from claim_detection.claim_checkability import ClaimCheckabilityClassifier
from claim_detection.claim_type_classifier import ClaimTypeClassifier


def set_env(enabled: bool, checkpoint: str | None, device: str | None):
    if enabled:
        os.environ['ENABLE_TRAINED_CLAIM_CHECKABILITY'] = '1'
        if checkpoint:
            os.environ['CLAIM_CHECKABILITY_CHECKPOINT'] = checkpoint
        if device:
            os.environ['CLAIM_CHECKABILITY_DEVICE'] = device
    else:
        os.environ.pop('ENABLE_TRAINED_CLAIM_CHECKABILITY', None)
        os.environ.pop('CLAIM_CHECKABILITY_CHECKPOINT', None)
        os.environ.pop('CLAIM_CHECKABILITY_DEVICE', None)


def run_mode(packet, mode_name: str, enabled: bool, checkpoint: str | None, device: str | None):
    set_env(enabled, checkpoint, device)
    claim_type = ClaimTypeClassifier()
    clf = ClaimCheckabilityClassifier()
    rows = []
    for item in packet:
        text = item['text']
        type_result = claim_type.classify(text)
        result = clf.classify(text, claim_type_result=type_result)
        label = getattr(result.get('label'), 'value', result.get('label'))
        subtype = getattr(result.get('subtype'), 'value', result.get('subtype'))
        rows.append({
            'text': text,
            'group': item.get('group'),
            'expected_label': item.get('expected_label'),
            'expected_subtype': item.get('expected_subtype'),
            'predicted_label': label,
            'predicted_subtype': subtype,
            'allowed': bool(result.get('allowed')),
            'confidence': float(result.get('confidence', 0.0) or 0.0),
            'decision_source': result.get('decision_source'),
            'claim_type': getattr(type_result.get('type'), 'value', type_result.get('type')),
            'claim_type_confidence': float(type_result.get('confidence', 0.0) or 0.0),
            'label_correct': label == item.get('expected_label'),
            'subtype_correct': subtype == item.get('expected_subtype'),
        })
    return rows


def summarize(rows):
    total = len(rows)
    label_acc = round(sum(1 for r in rows if r['label_correct']) / total, 4) if total else 0.0
    subtype_acc = round(sum(1 for r in rows if r['subtype_correct']) / total, 4) if total else 0.0
    by_group = defaultdict(lambda: {'total': 0, 'label_correct': 0, 'subtype_correct': 0})
    mistakes = []
    for row in rows:
        bucket = by_group[row['group']]
        bucket['total'] += 1
        bucket['label_correct'] += int(row['label_correct'])
        bucket['subtype_correct'] += int(row['subtype_correct'])
        if not row['label_correct'] or not row['subtype_correct']:
            mistakes.append(row)
    group_summary = {}
    for group, vals in by_group.items():
        group_summary[group] = {
            'total': vals['total'],
            'label_accuracy': round(vals['label_correct'] / vals['total'], 4),
            'subtype_accuracy': round(vals['subtype_correct'] / vals['total'], 4),
        }
    return {
        'total': total,
        'label_accuracy': label_acc,
        'subtype_accuracy': subtype_acc,
        'group_summary': group_summary,
        'mistakes': mistakes,
        'predicted_label_distribution': dict(Counter(r['predicted_label'] for r in rows)),
        'predicted_subtype_distribution': dict(Counter(r['predicted_subtype'] for r in rows)),
    }


def main():
    parser = argparse.ArgumentParser(description='Compare heuristic and trained claim-checkability gate outputs.')
    parser.add_argument('--packet', default='benchmark_claims/claim_checkability_eval_packet_v1.json')
    parser.add_argument('--checkpoint', default='checkpoints/claim_checkability/v2_run1')
    parser.add_argument('--device', default='cpu')
    parser.add_argument('--output', default='logs/claim_checkability_eval_packet_v1_results.json')
    args = parser.parse_args()

    packet = json.loads(Path(args.packet).read_text(encoding='utf-8'))
    heuristic_rows = run_mode(packet, 'heuristic', enabled=False, checkpoint=None, device=None)
    trained_rows = run_mode(packet, 'trained', enabled=True, checkpoint=args.checkpoint, device=args.device)

    heuristic_summary = summarize(heuristic_rows)
    trained_summary = summarize(trained_rows)

    comparison = []
    for h, t in zip(heuristic_rows, trained_rows):
        comparison.append({
            'text': h['text'],
            'group': h['group'],
            'expected_label': h['expected_label'],
            'expected_subtype': h['expected_subtype'],
            'heuristic_label': h['predicted_label'],
            'heuristic_subtype': h['predicted_subtype'],
            'trained_label': t['predicted_label'],
            'trained_subtype': t['predicted_subtype'],
            'heuristic_label_correct': h['label_correct'],
            'trained_label_correct': t['label_correct'],
            'heuristic_subtype_correct': h['subtype_correct'],
            'trained_subtype_correct': t['subtype_correct'],
        })

    payload = {
        'packet': args.packet,
        'checkpoint': args.checkpoint,
        'heuristic': heuristic_summary,
        'trained': trained_summary,
        'comparison': comparison,
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')

    print('Heuristic label accuracy:', heuristic_summary['label_accuracy'])
    print('Trained label accuracy:', trained_summary['label_accuracy'])
    print('Heuristic subtype accuracy:', heuristic_summary['subtype_accuracy'])
    print('Trained subtype accuracy:', trained_summary['subtype_accuracy'])
    print('Saved to', out)


if __name__ == '__main__':
    main()
