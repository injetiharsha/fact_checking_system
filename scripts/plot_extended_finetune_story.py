from __future__ import annotations

import json
import textwrap
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(r'f:/fact_checking_system')
RUN_SUMMARY = ROOT / 'training_artifacts' / 'recovered_metrics' / 'run_summary.csv'
PACKET_SUMMARY = ROOT / 'training_artifacts' / 'recovered_metrics' / 'benchmark_packets' / 'benchmark_packet_summary.csv'
OUT_DIR = ROOT / 'training_artifacts' / 'recovered_metrics' / 'finetune_story'
OUT_DIR.mkdir(parents=True, exist_ok=True)

CLAIM_CHECKABILITY_LADDER = [
    ('v2_run2', 'v2', 'curated local + ClaimBuster-mapped factuality baseline', 'next: broaden multilingual phrasing coverage'),
    ('v3_multilingual_run1', 'v3 multi', 'multilingual residual follow-up for non-English claims', 'next: add a larger residual follow-up and retest stability'),
    ('v4_multilingual_internet', 'v4 residual+', 'larger multilingual residual expansion after v3', 'next: refresh with a broader public multilingual factual-claim mix'),
    ('v5_public_large_multilingual', 'v5 public', 'larger public multilingual factual-claim refresh', 'latest preserved broad checkability run'),
]

PACKET_STAGES = [
    ('legacy_promoted', 'RFP2+V9+V2 | lock'),
    ('latest_locked', 'PHF+V9+V5 | lock'),
    ('raw_latest', 'PHF+V9+V5 | rv2+vv2'),
]

LOG_LOOKUP = {
    ('legacy_promoted', 30): ROOT / 'logs' / 'parallel_test_results_restorefast_patch2.json',
    ('latest_locked', 30): ROOT / 'logs' / 'parallel_test_results_env_30.json',
    ('raw_latest', 30): ROOT / 'logs' / 'parallel_test_results_env_30_raw.json',
    ('legacy_promoted', 50): ROOT / 'logs' / 'robust_mixed_50_restorefast_patch2.json',
    ('latest_locked', 50): ROOT / 'logs' / 'robust_mixed_50_env_latest.json',
    ('raw_latest', 50): ROOT / 'logs' / 'robust_mixed_50_env_raw.json',
    ('legacy_promoted', 68): ROOT / 'logs' / 'claim_seed_100_mixed_v1_benchmark_restorefast_patch2.json',
    ('latest_locked', 68): ROOT / 'logs' / 'claim_seed_100_mixed_v1_benchmark_env_latest.json',
    ('raw_latest', 68): ROOT / 'logs' / 'claim_seed_100_mixed_v1_benchmark_env_raw.json',
}

STORY_KEY = (
    'Story view: labels explain why we upgraded next. '
    'Where epoch history is missing, the chart stays a version ladder instead of a fake cumulative timeline.'
)


def wrap(text: str, width: int = 24) -> str:
    return '\n'.join(textwrap.wrap(text, width=width))


def add_footer(fig, text: str) -> None:
    fig.text(0.01, 0.01, text, ha='left', va='bottom', fontsize=10, color='#444444')


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def plot_claim_checkability(summary: pd.DataFrame) -> None:
    cc = summary[summary['task'] == 'claim_checkability'].copy()
    xs, labels, eval_vals, test_vals = [], [], [], []
    fig, ax = plt.subplots(figsize=(21, 12), dpi=220)

    for idx, (run, label, reason, next_note) in enumerate(CLAIM_CHECKABILITY_LADDER):
        xs.append(idx)
        labels.append(label)
        row = cc[cc['run_name'] == run]
        if row.empty:
            eval_vals.append(None)
            test_vals.append(None)
            ax.scatter(idx, 0.03, marker='x', color='#999999', s=160, linewidths=2.5)
            ax.text(idx, 0.07, 'metrics missing', ha='center', fontsize=10)
            continue
        row = row.iloc[0]
        eval_v = float(row['final_eval_accuracy']) if pd.notna(row['final_eval_accuracy']) else None
        test_v = float(row['final_test_accuracy']) if pd.notna(row['final_test_accuracy']) else None
        epoch_v = float(row['final_epoch']) if pd.notna(row['final_epoch']) else None
        coverage = str(row['coverage'])
        eval_vals.append(eval_v)
        test_vals.append(test_v)
        if eval_v is not None:
            ax.scatter(idx, eval_v, color='#0d3b66', s=130, zorder=5)
            ax.text(idx, eval_v + 0.02, f'eval {eval_v:.3f}', ha='center', fontsize=10, color='#0d3b66')
        if test_v is not None:
            ax.scatter(idx, test_v, color='#b23a48', s=130, zorder=5)
            ax.text(idx, test_v - 0.04, f'test {test_v:.3f}', ha='center', fontsize=10, color='#b23a48')
        meta = []
        if epoch_v is not None:
            meta.append(f'{epoch_v:.0f} epochs')
        if coverage == 'final_only':
            meta.append('final metrics only')
        elif coverage == 'curve_recoverable':
            meta.append('curve history preserved')
        ax.text(idx, 0.79, '\n'.join(meta), ha='center', va='top', fontsize=10, color='#444444')
        ax.text(idx, 0.735, wrap(reason, 26), ha='center', va='top', fontsize=10)
        if idx < len(CLAIM_CHECKABILITY_LADDER) - 1:
            anchor = max(v for v in [eval_v, test_v, 0.84] if v is not None)
            ax.annotate(
                wrap(next_note, 24),
                xy=(idx + 0.02, anchor + 0.008),
                xytext=(idx + 0.34, 0.98 if idx % 2 == 0 else 0.955),
                arrowprops={'arrowstyle': '->', 'color': '#666666', 'lw': 1.2},
                fontsize=9,
                ha='left',
                va='top',
                color='#444444',
            )

    line_x_eval = [x for x, y in zip(xs, eval_vals) if y is not None]
    line_y_eval = [y for y in eval_vals if y is not None]
    line_x_test = [x for x, y in zip(xs, test_vals) if y is not None]
    line_y_test = [y for y in test_vals if y is not None]
    ax.plot(line_x_eval, line_y_eval, color='#0d3b66', linewidth=2.8, label='Final eval accuracy')
    ax.plot(line_x_test, line_y_test, color='#b23a48', linewidth=2.8, linestyle='--', label='Final test accuracy')

    ax.set_title('Claim-checkability fine-tune story', fontsize=18)
    ax.set_ylabel('Accuracy', fontsize=13)
    ax.set_xticks(xs)
    ax.set_xticklabels(labels, fontsize=11)
    ax.set_ylim(0.72, 1.0)
    ax.grid(True, axis='y', alpha=0.25)
    ax.legend(loc='lower right', fontsize=11)
    add_footer(fig, STORY_KEY)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(OUT_DIR / 'claim_checkability_finetune_story.png', bbox_inches='tight')
    plt.close(fig)


def top_failures(path: Path, topn: int = 3) -> str:
    data = load_json(path)
    cats = data.get('benchmark_metrics', {}).get('failed_by_category', {})
    if not cats:
        return 'no failure breakdown preserved'
    items = sorted(cats.items(), key=lambda kv: (-kv[1], kv[0]))[:topn]
    return ', '.join(f'{k.replace("_", " ")} ({v})' for k, v in items)


def plot_benchmark_story(summary: pd.DataFrame) -> None:
    packet = summary[summary['claim_count'].isin([30, 50, 68])].copy()
    packet = packet[packet['stack_key'].isin([k for k, _ in PACKET_STAGES])].copy()
    stage_order = {k: i for i, (k, _) in enumerate(PACKET_STAGES)}
    packet['stage_idx'] = packet['stack_key'].map(stage_order)
    packet = packet.sort_values(['claim_count', 'stage_idx'])

    fig = plt.figure(figsize=(24, 15), dpi=220)
    gs = fig.add_gridspec(2, 1, height_ratios=[2.0, 1.6])
    ax = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1])

    colors = {30: '#2f7fb8', 50: '#2a9d8f', 68: '#b23a48'}
    for claim_count in [30, 50, 68]:
        sub = packet[packet['claim_count'] == claim_count]
        xs = sub['stage_idx'].tolist()
        ys = sub['accuracy'].tolist()
        ax.plot(xs, ys, marker='o', linewidth=3.0, markersize=10, color=colors[claim_count], label=f'{claim_count} claims')
        for _, row in sub.iterrows():
            ax.text(row['stage_idx'], row['accuracy'] + 0.013, f"{row['accuracy']:.3f}", ha='center', fontsize=10, color=colors[claim_count])

    ax.set_title('Benchmark claim packets across the last three meaningful stack upgrades', fontsize=20)
    ax.set_ylabel('Accuracy', fontsize=14)
    ax.set_xticks(range(len(PACKET_STAGES)))
    ax.set_xticklabels([label for _, label in PACKET_STAGES], fontsize=12)
    ax.set_ylim(0.72, 0.93)
    ax.grid(True, axis='y', alpha=0.25)
    ax.legend(loc='lower right', fontsize=12)

    ax2.axis('off')
    y = 0.98
    ax2.text(0.0, y, 'Packet-level upgrade story', fontsize=15, fontweight='bold', transform=ax2.transAxes)
    y -= 0.11
    for claim_count in [30, 50, 68]:
        legacy_row = packet[(packet['claim_count'] == claim_count) & (packet['stack_key'] == 'legacy_promoted')].iloc[0]
        latest_row = packet[(packet['claim_count'] == claim_count) & (packet['stack_key'] == 'latest_locked')].iloc[0]
        raw_row = packet[(packet['claim_count'] == claim_count) & (packet['stack_key'] == 'raw_latest')].iloc[0]
        latest_delta = raw_row['accuracy'] - latest_row['accuracy']
        legacy_delta = raw_row['accuracy'] - legacy_row['accuracy']
        latest_fail = top_failures(LOG_LOOKUP[('latest_locked', claim_count)])
        raw_fail = top_failures(LOG_LOOKUP[('raw_latest', claim_count)])
        lines = [
            f'{claim_count} claims: raw winner vs latest locked = {latest_delta:+.3f}; vs legacy promoted = {legacy_delta:+.3f}.',
            f'Latest locked saved failure mix: {latest_fail}.',
            f'Raw winner saved failure mix: {raw_fail}.',
        ]
        ax2.text(0.0, y, '\n'.join(lines), fontsize=11.5, transform=ax2.transAxes, va='top')
        y -= 0.28

    add_footer(fig, 'RFP2 = restorefast patch2 stance. PHF = public_hf_multilingual_v2 stance. V9 = relevance v9. V2/V5 = checkability versions. lock = retrieval_v2=0 and verifier_v2=0. rv2+vv2 = retrieval_v2=1 and verifier_v2=1.')
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(OUT_DIR / 'benchmark_claim_packet_upgrade_story.png', bbox_inches='tight')
    plt.close(fig)


def write_readme() -> None:
    text = '''# Fine-Tune Story Plots

These figures present the project as an upgrade story instead of isolated runs.

## Files

- `stance_cumulative_finetune_timeline.png`
- `relevance_upgrade_ladder.png`
- `claim_checkability_finetune_story.png`
- `benchmark_claim_packet_upgrade_story.png`

## Coverage by component

- `stance`: strongest story support; preserved continuation lineage and epoch lengths exist
- `relevance`: upgrade ladder only; most older epoch logs are missing
- `claim_checkability`: useful version ladder; later runs have curves, earlier ones preserve final metrics only
- `claim_type`: not enough preserved metrics for a meaningful story plot
- `context`: not enough preserved metrics for a meaningful story plot

## How to read the benchmark story

The benchmark figure tracks the last three meaningful full-stack stages on the `30`, `50`, and `68` claim packets:

1. legacy promoted stack
2. latest checkpoints with locked runtime
3. latest checkpoints with `retrieval_v2` and `verifier_v2` enabled

The text panel under the lines explains:

- how much the final raw winner gained over the latest locked stack
- how much it gained over the older promoted stack
- which failure categories were still dominant in the saved logs

## Caution

This is still a reconstruction from preserved artifacts. Where curve data is missing, the plots intentionally fall back to ladders and narrative annotations instead of inventing a continuous epoch history.
'''
    (OUT_DIR / 'README.md').write_text(text, encoding='utf-8')


def main() -> None:
    summary = pd.read_csv(RUN_SUMMARY)
    packet_summary = pd.read_csv(PACKET_SUMMARY)
    plot_claim_checkability(summary)
    plot_benchmark_story(packet_summary)
    write_readme()
    print(f'Updated story plots in {OUT_DIR}')


if __name__ == '__main__':
    main()
