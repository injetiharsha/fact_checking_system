from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(r'f:/fact_checking_system')
OUT_DIR = ROOT / 'training_artifacts' / 'dataset_breakdowns'
OUT_DIR.mkdir(parents=True, exist_ok=True)

BENCHMARK_LOGS = {
    '30_latest_locked': ROOT / 'logs' / 'parallel_test_results_env_30.json',
    '30_raw_latest': ROOT / 'logs' / 'parallel_test_results_env_30_raw.json',
    '50_latest_locked': ROOT / 'logs' / 'robust_mixed_50_env_latest.json',
    '50_raw_latest': ROOT / 'logs' / 'robust_mixed_50_env_raw.json',
    '68_latest_locked': ROOT / 'logs' / 'claim_seed_100_mixed_v1_benchmark_env_latest.json',
    '68_raw_latest': ROOT / 'logs' / 'claim_seed_100_mixed_v1_benchmark_env_raw.json',
}

CLAIM_CHECKABILITY_ORDER = ['v2', 'v3_multilingual', 'v4_multilingual_internet', 'v5_public_large_multilingual']
RELEVANCE_ORDER = ['v12_source_residual', 'v13_broad', 'v13_stage2_multilingual', 'v14_targeted']


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open('r', encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def save_bar(series: pd.Series, title: str, out_path: Path, ylabel: str = 'Count', figsize=(12, 7), rotate: int = 35, color: str = '#2f7fb8') -> None:
    if series.empty:
        return
    fig, ax = plt.subplots(figsize=figsize, dpi=220)
    series = series.sort_values(ascending=False)
    bars = ax.bar(series.index.astype(str), series.values, color=color)
    ax.set_title(title, fontsize=16)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.grid(True, axis='y', alpha=0.25)
    ax.tick_params(axis='x', rotation=rotate, labelsize=10)
    for bar, value in zip(bars, series.values):
        ax.text(bar.get_x() + bar.get_width() / 2, value, str(int(value)), ha='center', va='bottom', fontsize=9)
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches='tight')
    plt.close(fig)


def save_horizontal(series: pd.Series, title: str, out_path: Path, figsize=(11, 7), color: str = '#2f7fb8') -> None:
    if series.empty:
        return
    series = series.sort_values(ascending=True)
    fig, ax = plt.subplots(figsize=figsize, dpi=220)
    bars = ax.barh(series.index.astype(str), series.values, color=color)
    ax.set_title(title, fontsize=16)
    ax.set_xlabel('Count', fontsize=12)
    ax.grid(True, axis='x', alpha=0.25)
    for bar, value in zip(bars, series.values):
        ax.text(value, bar.get_y() + bar.get_height() / 2, f' {int(value)}', va='center', fontsize=9)
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches='tight')
    plt.close(fig)


def save_grouped_bars(df: pd.DataFrame, title: str, out_path: Path, figsize=(14, 8), rotate: int = 25) -> None:
    if df.empty:
        return
    fig, ax = plt.subplots(figsize=figsize, dpi=220)
    df.plot(kind='bar', ax=ax, colormap='tab20')
    ax.set_title(title, fontsize=16)
    ax.set_ylabel('Count', fontsize=12)
    ax.grid(True, axis='y', alpha=0.25)
    ax.tick_params(axis='x', rotation=rotate, labelsize=10)
    ax.legend(fontsize=9, loc='upper right')
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches='tight')
    plt.close(fig)


def save_stacked(df: pd.DataFrame, title: str, out_path: Path, figsize=(14, 8), rotate: int = 25) -> None:
    if df.empty:
        return
    fig, ax = plt.subplots(figsize=figsize, dpi=220)
    df.plot(kind='bar', stacked=True, ax=ax, colormap='tab20')
    ax.set_title(title, fontsize=16)
    ax.set_ylabel('Count', fontsize=12)
    ax.grid(True, axis='y', alpha=0.25)
    ax.tick_params(axis='x', rotation=rotate, labelsize=10)
    ax.legend(fontsize=9, loc='upper right')
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches='tight')
    plt.close(fig)


def save_donut(series: pd.Series, title: str, out_path: Path, figsize=(8, 8)) -> None:
    if series.empty:
        return
    series = series[series > 0].sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=figsize, dpi=220)
    ax.pie(
        series.values,
        labels=series.index.astype(str),
        autopct=lambda pct: f'{pct:.1f}%' if pct >= 3 else '',
        startangle=90,
        textprops={'fontsize': 10},
        wedgeprops={'width': 0.45, 'edgecolor': 'white'},
    )
    ax.set_title(title, fontsize=16)
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches='tight')
    plt.close(fig)


def save_line(df: pd.DataFrame, title: str, out_path: Path, ylabel: str = 'Rows', figsize=(13, 7)) -> None:
    if df.empty:
        return
    fig, ax = plt.subplots(figsize=figsize, dpi=220)
    colors = ['#2f7fb8', '#2a9d8f', '#b23a48', '#6f4e7c', '#f4a261']
    for col, color in zip(df.columns, colors):
        ax.plot(df.index.astype(str), df[col], marker='o', linewidth=2.5, markersize=8, label=col, color=color)
        for x, y in zip(df.index.astype(str), df[col]):
            ax.text(x, y, str(int(y)), ha='center', va='bottom', fontsize=9)
    ax.set_title(title, fontsize=16)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.grid(True, axis='y', alpha=0.25)
    ax.legend(fontsize=10, loc='best')
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches='tight')
    plt.close(fig)


def explicit_language_counts(rows: list[dict]) -> Counter:
    counts: Counter = Counter()
    for row in rows:
        lang = row.get('language') or row.get('lang')
        if lang:
            counts[str(lang)] += 1
    return counts


def classify_script(text: str) -> str:
    if any(ord(ch) > 127 for ch in text):
        return 'non_ascii_claim_text'
    return 'ascii_claim_text'


def classify_benchmark_language(text: str) -> str:
    if not text:
        return 'unknown'
    if any('\u0c00' <= ch <= '\u0c7f' for ch in text):
        return 'te_or_kn_or_ml_block'
    if any('\u0900' <= ch <= '\u097f' for ch in text):
        return 'hi_devanagari'
    if any(ord(ch) > 127 for ch in text):
        return 'other_non_ascii'
    return 'en_ascii'


def classify_text_script(text: str) -> str:
    if not text:
        return 'unknown'
    if any('\u0900' <= ch <= '\u097f' for ch in text):
        return 'hi_devanagari'
    if any('\u0b80' <= ch <= '\u0bff' for ch in text):
        return 'ta_tamil'
    if any('\u0c00' <= ch <= '\u0c7f' for ch in text):
        return 'te_kn_ml_block'
    if any(ord(ch) > 127 for ch in text):
        return 'other_non_ascii'
    return 'en_ascii'


def bucket_data_type(source: str, extra: str = '') -> str:
    text = f'{source} {extra}'.lower()
    if 'generated' in text:
        return 'generated'
    if 'official' in text:
        return 'official'
    if 'claimbuster' in text or 'averitec' in text or 'public' in text:
        return 'public'
    if 'internet' in text or 'online' in text or 'web' in text:
        return 'online_curated'
    if 'residual' in text:
        return 'residual'
    if 'manual' in text or 'seed' in text or 'curated' in text:
        return 'manual_seed'
    return 'other'


def current_stack_source_type_mix() -> tuple[pd.Series, pd.Series, pd.Series]:
    cc_rows = load_jsonl(ROOT / 'data' / 'claim_checkability' / 'v5_public_large_multilingual' / 'train.jsonl')
    rel_rows = load_jsonl(ROOT / 'data' / 'relevance' / 'v9' / 'train.jsonl')
    cc_counts = Counter(bucket_data_type(str(r.get('source', ''))) for r in cc_rows)
    rel_counts = Counter(bucket_data_type(str(r.get('source', '')), str(r.get('selection_origin', ''))) for r in rel_rows)
    combined = Counter(cc_counts)
    combined.update(rel_counts)
    return pd.Series(cc_counts), pd.Series(rel_counts), pd.Series(combined)


def plot_claim_checkability() -> dict:
    base = ROOT / 'data' / 'claim_checkability'
    label_rows = {}
    source_rows = {}
    growth_rows = []
    summary = []
    for version in CLAIM_CHECKABILITY_ORDER:
        meta_path = base / version / 'metadata.json'
        train_path = base / version / 'train.jsonl'
        meta = load_json(meta_path) if meta_path.exists() else {}
        label_dist = meta.get('label_distribution')
        if label_dist:
            label_rows[version] = label_dist
        if 'sources' in meta:
            source_rows[version] = meta['sources']
        rows = load_jsonl(train_path) if train_path.exists() else []
        growth_rows.append({'version': version, 'train_rows': len(rows)})
        summary.append({
            'dataset': version,
            'train_rows': len(rows),
            'has_explicit_language': sum(1 for r in rows if r.get('language') or r.get('lang')),
            'distinct_labels': len({r.get('label') for r in rows if r.get('label') is not None}),
            'distinct_sources': len({r.get('source') for r in rows if r.get('source') is not None}),
        })
    label_df = pd.DataFrame(label_rows).fillna(0).T.reindex(CLAIM_CHECKABILITY_ORDER)
    source_df = pd.DataFrame(source_rows).fillna(0).T.reindex(CLAIM_CHECKABILITY_ORDER)
    save_stacked(label_df, 'Claim-checkability label distribution by dataset version', OUT_DIR / 'claim_checkability_label_distribution_by_version.png', figsize=(16, 9))
    save_grouped_bars(source_df, 'Claim-checkability source mix by dataset version', OUT_DIR / 'claim_checkability_source_mix_by_version.png', figsize=(18, 10))
    save_horizontal(label_df.loc['v5_public_large_multilingual'], 'Claim-checkability v5 label share', OUT_DIR / 'claim_checkability_v5_label_share_bar.png', figsize=(11, 7), color='#2a9d8f')
    growth_df = pd.DataFrame(growth_rows).set_index('version')
    save_line(growth_df[['train_rows']], 'Claim-checkability dataset growth by version', OUT_DIR / 'claim_checkability_dataset_growth_by_version.png')
    return {'claim_checkability_summary': summary, 'claim_checkability_growth': growth_rows}


def plot_relevance() -> dict:
    base = ROOT / 'data' / 'relevance'
    source_rows = {}
    lang_rows = {}
    growth_rows = []
    summary = []
    for version in RELEVANCE_ORDER:
        meta_path = base / version / 'metadata.json'
        train_path = base / version / 'train.jsonl'
        meta = load_json(meta_path) if meta_path.exists() else {}
        if 'source_breakdown' in meta:
            source_rows[version] = meta['source_breakdown']
        rows = load_jsonl(train_path) if train_path.exists() else []
        lang_counts = explicit_language_counts(rows)
        if lang_counts:
            lang_rows[version] = dict(lang_counts)
        source_counts = Counter(str(r.get('source')) for r in rows if r.get('source') is not None)
        growth_rows.append({'version': version, 'train_rows': len(rows), 'explicit_language_rows': sum(lang_counts.values())})
        summary.append({
            'dataset': version,
            'train_rows': len(rows),
            'explicit_language_rows': sum(lang_counts.values()),
            'distinct_sources': len(source_counts),
            'positive_rows': sum(1 for r in rows if r.get('label') == 1),
            'negative_rows': sum(1 for r in rows if r.get('label') == 0),
        })
    if source_rows:
        source_df = pd.DataFrame(source_rows).fillna(0).T.reindex(RELEVANCE_ORDER)
        save_grouped_bars(source_df, 'Relevance source breakdown by dataset version', OUT_DIR / 'relevance_source_breakdown_by_version.png', figsize=(18, 10))
    if lang_rows:
        lang_df = pd.DataFrame(lang_rows).fillna(0).T.reindex([v for v in RELEVANCE_ORDER if v in lang_rows])
        save_stacked(lang_df, 'Relevance explicit language mix by dataset version', OUT_DIR / 'relevance_language_mix_by_version.png', figsize=(15, 9))
    growth_df = pd.DataFrame(growth_rows).set_index('version')
    save_line(growth_df[['train_rows', 'explicit_language_rows']], 'Relevance dataset growth and explicit language coverage', OUT_DIR / 'relevance_dataset_growth_by_version.png')
    return {'relevance_summary': summary, 'relevance_growth': growth_rows}


def plot_claim_type() -> dict:
    rows = load_jsonl(ROOT / 'data' / 'claim_type' / 'v1' / 'train.jsonl')
    label_counts = pd.Series(Counter(str(r.get('label')) for r in rows if r.get('label') is not None))
    source_counts = pd.Series(Counter(str(r.get('source')) for r in rows if r.get('source') is not None))
    save_donut(label_counts, 'Claim-type label share (train split)', OUT_DIR / 'claim_type_label_share_donut.png')
    save_bar(source_counts, 'Claim-type source distribution (train split)', OUT_DIR / 'claim_type_source_distribution.png', rotate=18, figsize=(13, 7), color='#2a9d8f')
    return {'claim_type_train_rows': len(rows)}


def plot_context() -> dict:
    rows = load_jsonl(ROOT / 'data' / 'context' / 'v2' / 'train.jsonl')
    label_counts = pd.Series(Counter(str(r.get('label')) for r in rows if r.get('label') is not None))
    subcat_counts = pd.Series(Counter(str(r.get('subcategory')) for r in rows if r.get('subcategory') is not None)).sort_values(ascending=False)
    source_counts = pd.Series(Counter(str(r.get('source')) for r in rows if r.get('source') is not None))
    save_donut(label_counts, 'Context category share (v2 train split)', OUT_DIR / 'context_category_share_v2_donut.png')
    save_bar(subcat_counts.head(12), 'Context top subcategory distribution (v2 train split)', OUT_DIR / 'context_top_subcategory_distribution_v2.png', rotate=28, figsize=(16, 8), color='#b23a48')
    save_donut(source_counts, 'Context source share (v2 train split)', OUT_DIR / 'context_source_share_v2_donut.png')
    return {'context_v2_train_rows': len(rows), 'context_v2_distinct_subcategories': int(subcat_counts.size)}


def benchmark_failure_breakdowns() -> dict:
    category_rows = {}
    tag_rows = {}
    script_rows = {}
    language_rows = {}
    metric_rows = []
    summary = []
    for key, path in BENCHMARK_LOGS.items():
        data = load_json(path)
        metrics = data.get('benchmark_metrics', {})
        category_rows[key] = metrics.get('failed_by_category', {})
        tag_rows[key] = metrics.get('failed_by_claim_tag', {})
        script_counter: Counter = Counter()
        lang_counter: Counter = Counter()
        for item in metrics.get('failed_claims', []):
            claim = item.get('claim', '')
            script_counter[classify_script(claim)] += 1
            lang_counter[classify_benchmark_language(claim)] += 1
        script_rows[key] = dict(script_counter)
        language_rows[key] = dict(lang_counter)
        metric_rows.append({
            'benchmark': key,
            'accuracy': metrics.get('accuracy'),
            'neutral_rate': metrics.get('neutral_rate'),
            'false_positive_rate': metrics.get('false_positive_rate'),
            'false_negative_rate': metrics.get('false_negative_rate'),
        })
        summary.append({
            'benchmark': key,
            'accuracy': metrics.get('accuracy'),
            'adjusted_accuracy': metrics.get('adjusted_accuracy_excluding_blocked'),
            'neutral_rate': metrics.get('neutral_rate'),
            'num_failed_categories': len(metrics.get('failed_by_category', {})),
            'num_failed_claims': len(metrics.get('failed_claims', [])),
        })
    category_df = pd.DataFrame(category_rows).fillna(0).T
    tag_df = pd.DataFrame(tag_rows).fillna(0).T
    script_df = pd.DataFrame(script_rows).fillna(0).T
    language_df = pd.DataFrame(language_rows).fillna(0).T
    metric_df = pd.DataFrame(metric_rows).set_index('benchmark')
    save_stacked(category_df, 'Benchmark failure categories by packet and stack', OUT_DIR / 'benchmark_failure_categories_by_packet_and_stack.png', figsize=(18, 9))
    save_grouped_bars(tag_df, 'Benchmark failed-claim logical tags by packet and stack', OUT_DIR / 'benchmark_failed_claim_tags_by_packet_and_stack.png', figsize=(18, 9), rotate=18)
    save_stacked(script_df, 'Benchmark failed-claim text script mix by packet and stack', OUT_DIR / 'benchmark_failed_claim_script_mix_by_packet_and_stack.png', figsize=(16, 8))
    if not language_df.empty:
        save_grouped_bars(language_df, 'Benchmark failed-claim language/script buckets by packet and stack', OUT_DIR / 'benchmark_failed_claim_language_buckets.png', figsize=(18, 9), rotate=18)
    save_grouped_bars(metric_df[['accuracy', 'neutral_rate', 'false_positive_rate', 'false_negative_rate']], 'Benchmark accuracy and error rates by packet and stack', OUT_DIR / 'benchmark_accuracy_error_by_packet_and_stack.png', figsize=(18, 9), rotate=18)
    return {'benchmark_failure_summary': summary}


def plot_data_evolution(claim_rows: list[dict], relevance_rows: list[dict]) -> None:
    cc_df = pd.DataFrame(claim_rows).set_index('version')
    rel_df = pd.DataFrame(relevance_rows).set_index('version')
    fig, axes = plt.subplots(2, 2, figsize=(22, 14), dpi=220)

    axes[0, 0].plot(cc_df.index, cc_df['train_rows'], marker='o', linewidth=2.5, color='#2f7fb8')
    axes[0, 0].set_title('Claim-checkability train rows by version')
    axes[0, 0].grid(True, axis='y', alpha=0.25)
    for x, y in zip(cc_df.index, cc_df['train_rows']):
        axes[0, 0].text(x, y, str(int(y)), ha='center', va='bottom', fontsize=9)

    axes[0, 1].plot(rel_df.index, rel_df['train_rows'], marker='o', linewidth=2.5, color='#2a9d8f')
    axes[0, 1].set_title('Relevance train rows by version')
    axes[0, 1].grid(True, axis='y', alpha=0.25)
    for x, y in zip(rel_df.index, rel_df['train_rows']):
        axes[0, 1].text(x, y, str(int(y)), ha='center', va='bottom', fontsize=9)

    latest_cc_meta = load_json(ROOT / 'data' / 'claim_checkability' / 'v5_public_large_multilingual' / 'metadata.json')
    cc_labels = pd.Series(latest_cc_meta.get('label_distribution', {})).sort_values(ascending=False)
    axes[1, 0].barh(cc_labels.index.astype(str), cc_labels.values, color='#6f4e7c')
    axes[1, 0].set_title('Claim-checkability v5 label share')
    axes[1, 0].grid(True, axis='x', alpha=0.25)

    if 'explicit_language_rows' in rel_df.columns:
        axes[1, 1].bar(rel_df.index.astype(str), rel_df['explicit_language_rows'], color='#b23a48')
        axes[1, 1].set_title('Relevance explicit language rows by version')
        axes[1, 1].grid(True, axis='y', alpha=0.25)
        for x, y in zip(rel_df.index.astype(str), rel_df['explicit_language_rows']):
            axes[1, 1].text(x, y, str(int(y)), ha='center', va='bottom', fontsize=9)

    fig.suptitle('Data evolution across the main training datasets', fontsize=20)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(OUT_DIR / 'data_evolution_figure_for_appendix.png', bbox_inches='tight')
    plt.close(fig)


def plot_major_stack_composition() -> None:
    cc_rows = load_jsonl(ROOT / 'data' / 'claim_checkability' / 'v5_public_large_multilingual' / 'train.jsonl')
    rel_rows = load_jsonl(ROOT / 'data' / 'relevance' / 'v9' / 'train.jsonl')
    rel_multi_rows = load_jsonl(ROOT / 'data' / 'relevance' / 'v13_stage2_multilingual' / 'train.jsonl')
    ct_rows = load_jsonl(ROOT / 'data' / 'claim_type' / 'v1' / 'train.jsonl')
    ctx_rows = load_jsonl(ROOT / 'data' / 'context' / 'v2' / 'train.jsonl')
    cc_meta = load_json(ROOT / 'data' / 'claim_checkability' / 'v5_public_large_multilingual' / 'metadata.json')

    cc_label = pd.Series(cc_meta.get('label_distribution', {})).sort_values(ascending=True)
    ct_label = pd.Series(Counter(str(r.get('label')) for r in ct_rows if r.get('label') is not None)).sort_values(ascending=False)
    ctx_cat = pd.Series(Counter(str(r.get('label')) for r in ctx_rows if r.get('label') is not None)).sort_values(ascending=False)
    ctx_sub = pd.Series(Counter(str(r.get('subcategory')) for r in ctx_rows if r.get('subcategory') is not None)).sort_values(ascending=False).head(10)
    rel_multi_lang = pd.Series(Counter(str(r.get('language')) for r in rel_multi_rows if r.get('language'))).sort_values(ascending=True)
    rel_type = pd.Series(Counter(bucket_data_type(str(r.get('source', '')), str(r.get('selection_origin', ''))) for r in rel_rows)).sort_values(ascending=False)
    cc_type = pd.Series(Counter(bucket_data_type(str(r.get('source', ''))) for r in cc_rows)).sort_values(ascending=False)
    combined_type = pd.DataFrame({'relevance_v9': rel_type, 'checkability_v5': cc_type}).fillna(0)

    fig, axes = plt.subplots(3, 2, figsize=(24, 20), dpi=220)

    axes[0, 0].barh(cc_label.index.astype(str), cc_label.values, color='#2f7fb8')
    axes[0, 0].set_title('Claim-checkability v5 label share')
    axes[0, 0].grid(True, axis='x', alpha=0.25)

    axes[0, 1].pie(
        ct_label.values,
        labels=ct_label.index.astype(str),
        autopct=lambda pct: f'{pct:.1f}%' if pct >= 4 else '',
        startangle=90,
        textprops={'fontsize': 9},
        colors=['#0d3b66', '#2a9d8f', '#e9c46a', '#e76f51', '#b23a48'],
    )
    axes[0, 1].set_title('Claim-type train label share')

    ctx_colors = ['#264653', '#2a9d8f', '#8ab17d', '#e9c46a', '#f4a261', '#e76f51', '#b56576', '#6d597a']
    axes[1, 0].pie(
        ctx_cat.values,
        labels=ctx_cat.index.astype(str),
        autopct=lambda pct: f'{pct:.1f}%' if pct >= 4 else '',
        startangle=90,
        textprops={'fontsize': 9},
        colors=ctx_colors[: len(ctx_cat)],
    )
    axes[1, 0].set_title('Context v2 category share')

    axes[1, 1].barh(ctx_sub.index.astype(str), ctx_sub.values, color='#b23a48')
    axes[1, 1].set_title('Context v2 top subcategories')
    axes[1, 1].grid(True, axis='x', alpha=0.25)

    axes[2, 0].barh(rel_multi_lang.index.astype(str), rel_multi_lang.values, color='#f4a261')
    axes[2, 0].set_title('Relevance multilingual train languages (v13 stage2)')
    axes[2, 0].grid(True, axis='x', alpha=0.25)
    for i, v in enumerate(rel_multi_lang.values):
        axes[2, 0].text(v, i, f' {int(v)}', va='center', fontsize=9)

    combined_type.plot(kind='bar', ax=axes[2, 1], colormap='tab20')
    axes[2, 1].set_title('Current stack data-type buckets')
    axes[2, 1].set_ylabel('Rows')
    axes[2, 1].grid(True, axis='y', alpha=0.25)
    axes[2, 1].tick_params(axis='x', rotation=20)

    fig.suptitle('Current stack data composition overview', fontsize=22)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(OUT_DIR / 'current_stack_data_composition_overview.png', bbox_inches='tight')
    plt.close(fig)


def write_summary(all_parts: dict) -> None:
    lines = [
        '# Dataset Breakdown Graphs',
        '',
        'Generated graphs cover the dimensions that are explicitly preserved in the repo.',
        '',
        '## Current runtime note',
        '',
        '- the current runtime uses `relevance/v9_run1`, not `v13_stage2_multilingual_run1`',
        '- `v13_stage2_multilingual_run1` was fine-tuned experimentally, but it is not the active checkpoint in `.env`',
        '',
        '## Recommended whole-stack / stack-upgrade figures',
        '',
        '- `stack_upgrade_accuracy.png`: best headline figure for upgrade performance across 30/50/68 packets',
        '- `stack_upgrade_component_matrix.png`: best companion figure for what changed at each stage',
        '- `benchmark_accuracy_error_by_packet_and_stack.png`: best error-profile figure for current-vs-legacy stack behavior',
        '- `current_stack_data_composition_overview.png`: best appendix figure for what the current stack data actually looks like',
        '',
        '## Caveats',
        '',
        '- many datasets do not preserve an explicit language field, so some language views are script buckets rather than gold language labels',
        '- the benchmark language buckets are inferred from script ranges in failed claims',
    ]
    (OUT_DIR / 'README.md').write_text('\n'.join(lines), encoding='utf-8')
    rows = []
    for key, value in all_parts.items():
        if isinstance(value, list):
            for row in value:
                row = dict(row)
                row['section'] = key
                rows.append(row)
    if rows:
        pd.DataFrame(rows).to_csv(OUT_DIR / 'dataset_breakdown_summary.csv', index=False)


def main() -> None:
    plt.style.use('default')
    collected = {}
    claim_res = plot_claim_checkability()
    rel_res = plot_relevance()
    collected.update(claim_res)
    collected.update(rel_res)
    collected.update(plot_claim_type())
    collected.update(plot_context())
    collected.update(benchmark_failure_breakdowns())
    plot_data_evolution(claim_res['claim_checkability_growth'], rel_res['relevance_growth'])
    plot_major_stack_composition()
    write_summary(collected)
    print(f'Wrote dataset breakdown outputs to {OUT_DIR}')


if __name__ == '__main__':
    main()






