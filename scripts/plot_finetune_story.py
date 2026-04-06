from __future__ import annotations

from pathlib import Path
import textwrap

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(r'f:/fact_checking_system')
RUN_SUMMARY = ROOT / 'training_artifacts' / 'recovered_metrics' / 'run_summary.csv'
OUT_DIR = ROOT / 'training_artifacts' / 'recovered_metrics' / 'finetune_story'
OUT_DIR.mkdir(parents=True, exist_ok=True)

STANCE_LINEAGE = [
    {
        'run': 'stage1_public_small_restorefast',
        'label': 'stage1 public\nrestorefast',
        'reason': 'public multilingual warm-start',
        'upgrade': 'hardcase misses and support/refute confusion',
    },
    {
        'run': 'stage2_hardcases_v3_bias_restorefast',
        'label': 'v3 bias\nrestorefast',
        'reason': 'continue from stage1 on hardcases',
        'upgrade': 'bias packet gaps remained on small evals',
    },
    {
        'run': 'stage2_hardcases_v3_bias_restorefast_patch1',
        'label': 'patch1',
        'reason': 'targeted patch on persistent failures',
        'upgrade': 'still needed one more small corrective pass',
    },
    {
        'run': 'stage2_hardcases_v3_bias_restorefast_patch2',
        'label': 'patch2',
        'reason': 'stabilize restorefast checkpoint',
        'upgrade': 'needed broader multilingual coverage next',
    },
    {
        'run': 'public_hf_multilingual_v2',
        'label': 'public HF\nmultilingual v2',
        'reason': 'large multilingual HF refresh from patch2',
        'upgrade': 'latest preserved broad stance run',
    },
]

RELEVANCE_LADDER = [
    ('v7_run1', 'v7', 'manual + curated seeds'),
    ('v8_run1', 'v8', 'phase-2 residual expansion'),
    ('v9_run1', 'v9', 'residual-backed evidence expansion'),
    ('v10_run1', 'v10', 'AVeriTeC official answers added'),
    ('v11_run1', 'v11', 'cleanup of noisy phase-2 cases'),
    ('v12_source_residual_run1', 'v12 src', 'source residual and official-source cases'),
    ('v13_broad_run1', 'v13 broad', 'merge broad residual + public sources'),
    ('v13_stage1_converted_run1', 'v13 s1', 'semantic stage-1 multilingual conversion'),
    ('v13_stage2_multilingual_run1', 'v13 s2', 'native multilingual surface-form adaptation'),
    ('v14_targeted_run1', 'v14', 'targeted residual follow-up'),
]

STACK_KEY = (
    'Labels show why each follow-up happened. '
    'Stance uses preserved cumulative epochs; relevance shows the upgrade ladder because older epoch logs are missing.'
)


def load_summary() -> pd.DataFrame:
    return pd.read_csv(RUN_SUMMARY)


def add_footer(fig, text: str) -> None:
    fig.text(0.01, 0.01, text, ha='left', va='bottom', fontsize=10, color='#444444')


def wrapped(text: str, width: int = 26) -> str:
    return '\n'.join(textwrap.wrap(text, width=width))


def plot_stance(summary: pd.DataFrame) -> None:
    stance = summary[summary['task'] == 'stance'].copy()
    records = []
    cumulative = 0.0
    for item in STANCE_LINEAGE:
        row = stance[stance['run_name'] == item['run']]
        if row.empty:
            continue
        row = row.iloc[0]
        epochs = float(row['final_epoch']) if pd.notna(row['final_epoch']) else 0.0
        start = cumulative
        end = cumulative + epochs
        cumulative = end
        records.append({
            **item,
            'epochs': epochs,
            'start': start,
            'end': end,
            'eval_acc': float(row['final_eval_accuracy']) if pd.notna(row['final_eval_accuracy']) else None,
            'test_acc': float(row['final_test_accuracy']) if pd.notna(row['final_test_accuracy']) else None,
        })

    if not records:
        return

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(24, 15), dpi=220, gridspec_kw={'height_ratios': [2.4, 1.45]}, sharex=True
    )

    colors = ['#d8e8f8', '#b7d5ee', '#96c1e3', '#6aa9d8', '#2f7fb8']
    endpoints = []
    evals = []
    tests = []
    for idx, rec in enumerate(records):
        color = colors[idx % len(colors)]
        ax1.axvspan(rec['start'], rec['end'], color=color, alpha=0.35)
        center = (rec['start'] + rec['end']) / 2
        if rec['eval_acc'] is not None:
            endpoints.append(rec['end'])
            evals.append(rec['eval_acc'])
            tests.append(rec['test_acc'])
            ax1.scatter(rec['end'], rec['eval_acc'], color='#0d3b66', s=110, zorder=5)
            if rec['test_acc'] is not None:
                ax1.scatter(rec['end'], rec['test_acc'], color='#b23a48', s=110, zorder=5)
            ax1.text(rec['end'], rec['eval_acc'] + 0.012, f"{rec['label']}\n{rec['eval_acc']:.3f}", ha='center', va='bottom', fontsize=10)
        ax2.barh([0], [rec['epochs']], left=[rec['start']], height=0.56, color=color, edgecolor='#1f3552')
        ax2.text(center, 0, f"{rec['label']}\n{rec['epochs']:.1f} ep", ha='center', va='center', fontsize=10)
        ax2.text(center, -0.60, wrapped(rec['reason'], 24), ha='center', va='top', fontsize=9, color='#333333')
        if idx < len(records) - 1:
            ax2.annotate(
                wrapped('upgrade: ' + rec['upgrade'], 24),
                xy=(rec['end'], 0.30),
                xytext=(rec['end'] + 0.20, 1.0 if idx % 2 == 0 else 1.32),
                arrowprops={'arrowstyle': '->', 'color': '#444444', 'lw': 1.3},
                fontsize=9,
                ha='left',
                va='bottom',
            )

    if endpoints:
        ax1.plot(endpoints, evals, color='#0d3b66', linewidth=2.8, label='Final eval accuracy')
        if any(v is not None for v in tests):
            test_x = [x for x, y in zip(endpoints, tests) if y is not None]
            test_y = [y for y in tests if y is not None]
            ax1.plot(test_x, test_y, color='#b23a48', linewidth=2.8, linestyle='--', label='Final test accuracy')

    ax1.set_title('Stance cumulative fine-tune timeline to latest preserved run', fontsize=20)
    ax1.set_ylabel('Accuracy', fontsize=14)
    ax1.set_ylim(0.72, 1.03)
    ax1.grid(True, axis='y', alpha=0.25)
    ax1.legend(loc='lower right', fontsize=12)

    ax2.set_title('Epoch spans and why the next fine-tune happened', fontsize=16)
    ax2.set_xlabel('Cumulative fine-tune epochs across lineage', fontsize=14)
    ax2.set_yticks([])
    ax2.set_ylim(-1.28, 1.95)
    ax2.tick_params(axis='x', labelsize=11)
    ax2.grid(False)

    add_footer(fig, STACK_KEY)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(OUT_DIR / 'stance_cumulative_finetune_timeline.png', bbox_inches='tight')
    plt.close(fig)


def plot_relevance(summary: pd.DataFrame) -> None:
    rel = summary[summary['task'] == 'relevance'].copy()
    fig, ax = plt.subplots(figsize=(24, 11), dpi=220)

    xs = list(range(len(RELEVANCE_LADDER)))
    eval_vals = []
    test_vals = []
    labels = []
    for idx, (run, short_label, reason) in enumerate(RELEVANCE_LADDER):
        row = rel[rel['run_name'] == run]
        labels.append(short_label)
        if row.empty:
            eval_vals.append(None)
            test_vals.append(None)
            ax.scatter(idx, 0.02, marker='x', color='#999999', s=150, linewidths=2.5)
            ax.text(idx, 0.06, 'metrics\nmissing', ha='center', va='bottom', fontsize=10, color='#666666')
        else:
            row = row.iloc[0]
            eval_v = float(row['final_eval_accuracy']) if pd.notna(row['final_eval_accuracy']) else None
            test_v = float(row['final_test_accuracy']) if pd.notna(row['final_test_accuracy']) else None
            eval_vals.append(eval_v)
            test_vals.append(test_v)
            if eval_v is not None:
                ax.scatter(idx, eval_v, color='#0d3b66', s=110, zorder=5)
                ax.text(idx, eval_v + 0.025, f'{eval_v:.3f}', ha='center', fontsize=10)
            if test_v is not None:
                ax.scatter(idx, test_v, color='#b23a48', s=110, zorder=5)

        ax.text(idx, -0.10, wrapped(reason, 19), ha='center', va='top', fontsize=9)

    eval_line_x = [x for x, y in zip(xs, eval_vals) if y is not None]
    eval_line_y = [y for y in eval_vals if y is not None]
    test_line_x = [x for x, y in zip(xs, test_vals) if y is not None]
    test_line_y = [y for y in test_vals if y is not None]
    if eval_line_x:
        ax.plot(eval_line_x, eval_line_y, color='#0d3b66', linewidth=2.6, label='Recovered final eval accuracy')
    if test_line_x:
        ax.plot(test_line_x, test_line_y, color='#b23a48', linewidth=2.6, linestyle='--', label='Recovered final test accuracy')

    ax.set_title('Relevance upgrade ladder with preserved-metric coverage', fontsize=20)
    ax.set_ylabel('Accuracy', fontsize=14)
    ax.set_xticks(xs)
    ax.set_xticklabels(labels, rotation=0, fontsize=11)
    ax.set_ylim(-0.18, 1.0)
    ax.grid(True, axis='y', alpha=0.25)
    ax.legend(loc='upper left', fontsize=12)

    add_footer(fig, STACK_KEY)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(OUT_DIR / 'relevance_upgrade_ladder.png', bbox_inches='tight')
    plt.close(fig)


def main() -> None:
    summary = load_summary()
    plot_stance(summary)
    plot_relevance(summary)
    print(f'Wrote story plots to {OUT_DIR}')


if __name__ == '__main__':
    main()
