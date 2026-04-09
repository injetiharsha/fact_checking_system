import os
import re
import gc
import math
import json
import time
import random
import warnings
from typing import Dict, List

import pandas as pd
import torch
from tqdm import tqdm
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from IndicTransToolkit.processor import IndicProcessor

warnings.filterwarnings("ignore")

# =========================================================
# CONFIG
# =========================================================

INPUT_CSV = r"F:\fact_checking_system\context_labeled_data_hierarchical.csv"
OUTPUT_DIR = r"F:\fact_checking_system\indictrans2_translation_7k"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# IndicTrans2
MODEL_NAME = "ai4bharat/indictrans2-en-indic-dist-200M"
# If you have enough VRAM and want the larger model:
# MODEL_NAME = "ai4bharat/indictrans2-en-indic-1B"

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
DTYPE = torch.float16 if DEVICE == "cuda" else torch.float32

# Selection target: 14 classes * 500 = 7000
TARGET_TOTAL = 7000
PER_CLASS_TARGET = 500
LEVEL_TARGETS = {
    "primary": 230,
    "secondary": 165,
    "tertiary": 105,
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

TARGET_LANGS = {
    "hi": "hin_Deva",
    "te": "tel_Telu",
    "ta": "tam_Taml",
    "ml": "mal_Mlym",
    "kn": "kan_Knda",
}

SOURCE_LANG = "eng_Latn"

# Filters
MIN_SCORE = 6.0
MIN_WORDS = 12
MAX_WORDS = 110
MIN_CHARS = 80
MAX_CHARS = 700
MAX_DUPLICATE_NGRAM_RATIO = 0.65

# Translation batching
BATCH_SIZE = 24 if DEVICE == "cuda" else 6
MAX_SOURCE_LENGTH = 256
MAX_TARGET_LENGTH = 256
NUM_BEAMS = 1  # faster; use 4 for higher quality but slower

SEED = 42
random.seed(SEED)

# =========================================================
# HELPERS
# =========================================================

def clean_text(text: str) -> str:
    if pd.isna(text):
        return ""
    text = str(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def word_count(text: str) -> int:
    return len(str(text).split())

def char_count(text: str) -> int:
    return len(str(text))

def repetitive_ratio(text: str, n: int = 3) -> float:
    words = str(text).lower().split()
    if len(words) < n:
        return 0.0
    ngrams = [" ".join(words[i:i+n]) for i in range(len(words) - n + 1)]
    if not ngrams:
        return 0.0
    return 1.0 - (len(set(ngrams)) / len(ngrams))

def length_quality(words: int, chars: int) -> float:
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

def safe_filename(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", name)

# =========================================================
# LOAD + FILTER
# =========================================================

def load_and_filter(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)

    required = [
        "text", "context_class", "relevance_level", "score"
    ]
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")

    # Preserve all original columns; just clean/augment
    df["text"] = df["text"].apply(clean_text)
    df["context_class"] = df["context_class"].astype(str).str.strip().str.lower()
    df["relevance_level"] = df["relevance_level"].astype(str).str.strip().str.lower()
    df["score"] = pd.to_numeric(df["score"], errors="coerce").fillna(0.0)

    df["word_len"] = df["text"].apply(word_count)
    df["char_len"] = df["text"].apply(char_count)
    df["repeat_ratio"] = df["text"].apply(repetitive_ratio)

    df = df[df["context_class"].isin(CLASS_ORDER)].copy()
    df = df[df["relevance_level"].isin(LEVEL_TARGETS.keys())].copy()
    df = df[df["score"] >= MIN_SCORE].copy()
    df = df[df["word_len"].between(MIN_WORDS, MAX_WORDS)].copy()
    df = df[df["char_len"].between(MIN_CHARS, MAX_CHARS)].copy()
    df = df[df["repeat_ratio"] <= MAX_DUPLICATE_NGRAM_RATIO].copy()

    # exact dedupe within class
    df = df.drop_duplicates(subset=["text", "context_class"]).reset_index(drop=True)

    df["level_weight"] = df["relevance_level"].map({
        "primary": 3,
        "secondary": 2,
        "tertiary": 1,
    })

    df["length_quality"] = df.apply(
        lambda r: length_quality(int(r["word_len"]), int(r["char_len"])),
        axis=1,
    )

    # High score + higher level + better length; slight penalty for long text
    df["selection_score"] = (
        df["score"] * 2.0
        + df["level_weight"] * 3.0
        + df["length_quality"] * 1.5
        - (df["char_len"] / 1000.0)
    )

    return df.reset_index(drop=True)

# =========================================================
# SELECT 7K BALANCED SUBSET
# =========================================================

def select_balanced_7k(df: pd.DataFrame) -> pd.DataFrame:
    picked = []

    for cls in CLASS_ORDER:
        cls_df = df[df["context_class"] == cls].copy()

        for level, target_n in LEVEL_TARGETS.items():
            sub = cls_df[cls_df["relevance_level"] == level].copy()
            sub = sub.sort_values(
                by=["selection_score", "score", "char_len"],
                ascending=[False, False, True],
            )
            picked.append(sub.head(target_n))

    out = pd.concat(picked, ignore_index=True)

    # fallback fill if some class-level bucket had fewer rows than target
    if len(out) < TARGET_TOTAL:
        missing = TARGET_TOTAL - len(out)
        selected_keys = set(zip(out["text"], out["context_class"]))
        remain = df[
            ~df.apply(lambda r: (r["text"], r["context_class"]) in selected_keys, axis=1)
        ].copy()
        remain = remain.sort_values(
            by=["selection_score", "score", "char_len"],
            ascending=[False, False, True],
        )
        out = pd.concat([out, remain.head(missing)], ignore_index=True)

    # final exact cap
    out = out.drop_duplicates(subset=["text", "context_class"]).head(TARGET_TOTAL).copy()

    # stable ordering
    out["context_class"] = pd.Categorical(out["context_class"], CLASS_ORDER, ordered=True)
    out["relevance_level"] = pd.Categorical(
        out["relevance_level"], ["primary", "secondary", "tertiary"], ordered=True
    )
    out = out.sort_values(
        by=["context_class", "relevance_level", "selection_score"],
        ascending=[True, True, False],
    ).reset_index(drop=True)

    # restore plain strings
    out["context_class"] = out["context_class"].astype(str)
    out["relevance_level"] = out["relevance_level"].astype(str)

    return out

# =========================================================
# SUMMARY
# =========================================================

def save_summaries(df: pd.DataFrame, prefix: str) -> None:
    by_class = df.groupby("context_class").agg(
        rows=("text", "count"),
        total_chars=("char_len", "sum"),
        avg_chars=("char_len", "mean"),
        avg_words=("word_len", "mean"),
    ).reset_index()

    by_level = df.groupby("relevance_level").agg(
        rows=("text", "count"),
        total_chars=("char_len", "sum"),
        avg_chars=("char_len", "mean"),
        avg_words=("word_len", "mean"),
    ).reset_index()

    by_class_level = df.groupby(["context_class", "relevance_level"]).agg(
        rows=("text", "count"),
        total_chars=("char_len", "sum"),
        avg_chars=("char_len", "mean"),
        avg_words=("word_len", "mean"),
    ).reset_index()

    by_class.to_csv(os.path.join(OUTPUT_DIR, f"{prefix}_summary_by_class.csv"), index=False)
    by_level.to_csv(os.path.join(OUTPUT_DIR, f"{prefix}_summary_by_level.csv"), index=False)
    by_class_level.to_csv(os.path.join(OUTPUT_DIR, f"{prefix}_summary_by_class_level.csv"), index=False)

# =========================================================
# LOAD INDICTRANS2
# =========================================================

def load_translation_stack():
    print(f"[INFO] Loading model: {MODEL_NAME}")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
    model = AutoModelForSeq2SeqLM.from_pretrained(
        MODEL_NAME,
        trust_remote_code=True,
        torch_dtype=DTYPE,
    )
    model.to(DEVICE)
    model.eval()

    ip = IndicProcessor(inference=True)
    return tokenizer, model, ip

# =========================================================
# TRANSLATION
# =========================================================

@torch.inference_mode()
def translate_batch(
    texts: List[str],
    tgt_lang: str,
    tokenizer,
    model,
    ip,
) -> List[str]:
    # IndicTrans2 recommended flow: preprocess_batch -> tokenize -> generate -> postprocess_batch
    batch = ip.preprocess_batch(
        texts,
        src_lang=SOURCE_LANG,
        tgt_lang=tgt_lang,
    )

    inputs = tokenizer(
        batch,
        truncation=True,
        padding="longest",
        max_length=MAX_SOURCE_LENGTH,
        return_tensors="pt",
    ).to(DEVICE)

    generated_tokens = model.generate(
        **inputs,
        max_length=MAX_TARGET_LENGTH,
        num_beams=NUM_BEAMS,
        do_sample=False,
    )

    decoded = tokenizer.batch_decode(
        generated_tokens,
        skip_special_tokens=True,
        clean_up_tokenization_spaces=True,
    )

    outputs = ip.postprocess_batch(decoded, lang=tgt_lang)
    return outputs

def translate_dataframe(
    df: pd.DataFrame,
    lang_code: str,
    tgt_lang_tag: str,
    tokenizer,
    model,
    ip,
) -> pd.DataFrame:
    records = []
    texts = df["text"].tolist()

    for start in tqdm(range(0, len(texts), BATCH_SIZE), desc=f"Translating {lang_code}"):
        end = min(start + BATCH_SIZE, len(texts))
        batch_texts = texts[start:end]

        try:
            translated = translate_batch(batch_texts, tgt_lang_tag, tokenizer, model, ip)
        except RuntimeError as e:
            if "out of memory" in str(e).lower() and DEVICE == "cuda":
                torch.cuda.empty_cache()
                gc.collect()
                smaller = max(1, BATCH_SIZE // 2)
                translated = []
                for s in range(0, len(batch_texts), smaller):
                    part = batch_texts[s:s+smaller]
                    translated.extend(translate_batch(part, tgt_lang_tag, tokenizer, model, ip))
            else:
                raise

        chunk_df = df.iloc[start:end].copy()
        chunk_df["original_text"] = chunk_df["text"]
        chunk_df["text"] = translated
        chunk_df["lang"] = lang_code
        chunk_df["source_type"] = "translated_indictrans2"
        records.append(chunk_df)

    out = pd.concat(records, ignore_index=True)
    return out

# =========================================================
# MAIN
# =========================================================

def main():
    print("[INFO] Reading and filtering raw CSV...")
    raw_df = load_and_filter(INPUT_CSV)
    save_summaries(raw_df, "raw_filtered")

    print(f"[INFO] Filtered pool rows: {len(raw_df)}")

    print("[INFO] Selecting balanced 7k subset...")
    selected_df = select_balanced_7k(raw_df)

    # save English subset
    english_out = selected_df.copy()
    english_out["original_text"] = english_out["text"]
    english_out["lang"] = "en"
    english_out["source_type"] = "original_english"

    english_path = os.path.join(OUTPUT_DIR, "selected_english_7k.csv")
    english_out.to_csv(english_path, index=False, encoding="utf-8")
    save_summaries(selected_df, "selected_7k")

    print(f"[INFO] Selected rows: {len(selected_df)}")
    print(selected_df["context_class"].value_counts().sort_index())
    print(selected_df["relevance_level"].value_counts().sort_index())

    tokenizer, model, ip = load_translation_stack()

    translated_frames = [english_out]

    for lang_code, tgt_lang_tag in TARGET_LANGS.items():
        print(f"\n[INFO] Translating to {lang_code} ({tgt_lang_tag})")
        translated_df = translate_dataframe(
            selected_df, lang_code, tgt_lang_tag, tokenizer, model, ip
        )
        lang_path = os.path.join(OUTPUT_DIR, f"translated_{lang_code}_7k.csv")
        translated_df.to_csv(lang_path, index=False, encoding="utf-8")
        translated_frames.append(translated_df)

    merged = pd.concat(translated_frames, ignore_index=True)
    merged_path = os.path.join(OUTPUT_DIR, "multilingual_context_dataset_7k_seed.csv")
    merged.to_csv(merged_path, index=False, encoding="utf-8")

    manifest = {
        "input_csv": INPUT_CSV,
        "model_name": MODEL_NAME,
        "device": DEVICE,
        "target_total": TARGET_TOTAL,
        "per_class_target": PER_CLASS_TARGET,
        "level_targets": LEVEL_TARGETS,
        "target_langs": TARGET_LANGS,
        "selected_rows": int(len(selected_df)),
        "merged_rows": int(len(merged)),
        "outputs": {
            "selected_english": english_path,
            "merged_multilingual": merged_path,
        },
    }
    with open(os.path.join(OUTPUT_DIR, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print("\n[SUCCESS] Done.")
    print(f"[INFO] English subset: {english_path}")
    print(f"[INFO] Multilingual merged: {merged_path}")

if __name__ == "__main__":
    main()