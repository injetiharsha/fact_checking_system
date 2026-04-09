import os
import re
import math
import pandas as pd

# =========================================================
# CONFIG
# =========================================================

INPUT_CSV = r"F:\fact_checking_system\context_labeled_data_hierarchical.csv"
OUTPUT_DIR = r"F:\fact_checking_system\translation_prep"
os.makedirs(OUTPUT_DIR, exist_ok=True)

CHAR_BUDGET = 400000   # make one master subset first
MIN_SCORE = 6.0
MIN_WORDS = 12
MAX_WORDS = 110
MIN_CHARS = 80
MAX_CHARS = 700

LEVEL_PRIORITY = {
    "primary": 3,
    "secondary": 2,
    "tertiary": 1
}

CLASS_ORDER = [
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

# =========================================================
# CLEANING
# =========================================================

def clean_text(text):
    if pd.isna(text):
        return ""
    text = str(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def word_count(text):
    return len(str(text).split())

def char_count(text):
    return len(str(text))

def too_repetitive(text):
    words = str(text).lower().split()
    if not words:
        return True
    unique_ratio = len(set(words)) / max(len(words), 1)
    return unique_ratio < 0.45

def length_quality(words, chars):
    # prefer medium-length contextual claims
    score = 0.0

    if 18 <= words <= 70:
        score += 3.0
    elif 12 <= words <= 90:
        score += 2.0
    else:
        score += 0.5

    if 120 <= chars <= 420:
        score += 3.0
    elif 80 <= chars <= 550:
        score += 2.0
    else:
        score += 0.5

    return score

# =========================================================
# LOAD + FILTER
# =========================================================

df = pd.read_csv(INPUT_CSV)

required_cols = [
    "text", "context_class", "relevance_level", "score"
]
for col in required_cols:
    if col not in df.columns:
        raise ValueError(f"Missing required column: {col}")

df["text"] = df["text"].apply(clean_text)
df["context_class"] = df["context_class"].astype(str).str.strip().str.lower()
df["relevance_level"] = df["relevance_level"].astype(str).str.strip().str.lower()
df["score"] = pd.to_numeric(df["score"], errors="coerce").fillna(0.0)

df["word_len"] = df["text"].apply(word_count)
df["char_len"] = df["text"].apply(char_count)

# basic filters
df = df[df["context_class"].isin(CLASS_ORDER)].copy()
df = df[df["relevance_level"].isin(LEVEL_PRIORITY.keys())].copy()
df = df[df["score"] >= MIN_SCORE].copy()
df = df[df["word_len"] >= MIN_WORDS].copy()
df = df[df["word_len"] <= MAX_WORDS].copy()
df = df[df["char_len"] >= MIN_CHARS].copy()
df = df[df["char_len"] <= MAX_CHARS].copy()
df = df[~df["text"].apply(too_repetitive)].copy()

# dedupe on text + class
df = df.drop_duplicates(subset=["text", "context_class"]).reset_index(drop=True)

# =========================================================
# ANALYSIS TABLES
# =========================================================

summary_class = df.groupby("context_class").agg(
    rows=("text", "count"),
    total_chars=("char_len", "sum"),
    avg_chars=("char_len", "mean"),
    avg_words=("word_len", "mean"),
).reset_index()

summary_level = df.groupby("relevance_level").agg(
    rows=("text", "count"),
    total_chars=("char_len", "sum"),
    avg_chars=("char_len", "mean"),
    avg_words=("word_len", "mean"),
).reset_index()

summary_class_level = df.groupby(["context_class", "relevance_level"]).agg(
    rows=("text", "count"),
    total_chars=("char_len", "sum"),
    avg_chars=("char_len", "mean"),
    avg_words=("word_len", "mean"),
).reset_index()

summary_class.to_csv(os.path.join(OUTPUT_DIR, "summary_by_class.csv"), index=False)
summary_level.to_csv(os.path.join(OUTPUT_DIR, "summary_by_level.csv"), index=False)
summary_class_level.to_csv(os.path.join(OUTPUT_DIR, "summary_by_class_level.csv"), index=False)

print("\n===== SUMMARY BY CLASS =====")
print(summary_class.sort_values("rows", ascending=False).to_string(index=False))

print("\n===== SUMMARY BY LEVEL =====")
print(summary_level.sort_values("rows", ascending=False).to_string(index=False))

print("\n===== SUMMARY BY CLASS x LEVEL =====")
print(summary_class_level.sort_values(["context_class", "relevance_level"]).to_string(index=False))

# =========================================================
# RANKING
# =========================================================

df["level_weight"] = df["relevance_level"].map(LEVEL_PRIORITY)
df["length_quality"] = df.apply(lambda r: length_quality(r["word_len"], r["char_len"]), axis=1)

# prefer useful rows, but also prefer shorter rows when quality is similar
df["selection_score"] = (
    df["score"] * 2.0 +
    df["level_weight"] * 3.0 +
    df["length_quality"] * 1.5 -
    (df["char_len"] / 1000.0)
)

# =========================================================
# BALANCED SELECTION UNDER BUDGET
# =========================================================

selected_rows = []
used_chars = 0

# split target budget per class evenly first
per_class_budget = CHAR_BUDGET // len(CLASS_ORDER)

for cls in CLASS_ORDER:
    cls_df = df[df["context_class"] == cls].copy()

    # within class, prefer primary > secondary > tertiary, then score
    cls_df = cls_df.sort_values(
        by=["level_weight", "selection_score", "score"],
        ascending=[False, False, False]
    )

    cls_used = 0
    for _, row in cls_df.iterrows():
        row_chars = int(row["char_len"])
        if cls_used + row_chars <= per_class_budget and used_chars + row_chars <= CHAR_BUDGET:
            selected_rows.append(row)
            cls_used += row_chars
            used_chars += row_chars

# second pass: fill remaining budget globally with best leftovers
selected_df = pd.DataFrame(selected_rows).drop_duplicates(subset=["text", "context_class"])
selected_keys = set(zip(selected_df["text"], selected_df["context_class"]))

remaining_df = df[~df.apply(lambda r: (r["text"], r["context_class"]) in selected_keys, axis=1)].copy()
remaining_df = remaining_df.sort_values(
    by=["level_weight", "selection_score", "score"],
    ascending=[False, False, False]
)

for _, row in remaining_df.iterrows():
    row_chars = int(row["char_len"])
    if used_chars + row_chars <= CHAR_BUDGET:
        selected_df = pd.concat([selected_df, pd.DataFrame([row])], ignore_index=True)
        used_chars += row_chars
    else:
        break

selected_df = selected_df.sort_values(
    by=["context_class", "level_weight", "score"],
    ascending=[True, False, False]
).reset_index(drop=True)

# =========================================================
# SAVE
# =========================================================

# keep original schema + analysis columns
selected_df.to_csv(os.path.join(OUTPUT_DIR, "translation_ready_subset.csv"), index=False)

selected_summary_class = selected_df.groupby("context_class").agg(
    rows=("text", "count"),
    total_chars=("char_len", "sum"),
    avg_chars=("char_len", "mean"),
).reset_index()

selected_summary_level = selected_df.groupby("relevance_level").agg(
    rows=("text", "count"),
    total_chars=("char_len", "sum"),
    avg_chars=("char_len", "mean"),
).reset_index()

selected_summary_class_level = selected_df.groupby(["context_class", "relevance_level"]).agg(
    rows=("text", "count"),
    total_chars=("char_len", "sum"),
    avg_chars=("char_len", "mean"),
).reset_index()

selected_summary_class.to_csv(os.path.join(OUTPUT_DIR, "selected_summary_by_class.csv"), index=False)
selected_summary_level.to_csv(os.path.join(OUTPUT_DIR, "selected_summary_by_level.csv"), index=False)
selected_summary_class_level.to_csv(os.path.join(OUTPUT_DIR, "selected_summary_by_class_level.csv"), index=False)

print("\n===== SELECTED SUBSET =====")
print(f"Rows selected: {len(selected_df)}")
print(f"Characters used: {used_chars} / {CHAR_BUDGET}")

print("\n===== SELECTED BY CLASS =====")
print(selected_summary_class.sort_values("rows", ascending=False).to_string(index=False))

print("\n===== SELECTED BY LEVEL =====")
print(selected_summary_level.sort_values("rows", ascending=False).to_string(index=False))