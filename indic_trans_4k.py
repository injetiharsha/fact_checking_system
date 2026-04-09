import os
import re
import gc
import json
import random
import warnings
from typing import List

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
OUTPUT_DIR = r"F:\fact_checking_system\indictrans2_translation_20k"
os.makedirs(OUTPUT_DIR, exist_ok=True)

MODEL_NAME = "ai4bharat/indictrans2-en-indic-dist-200M"

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
DTYPE = torch.float16 if DEVICE == "cuda" else torch.float32

# Final target:
# 5 languages × 4000 translated rows = 20000 translated rows total
ENGLISH_SOURCE_ROWS = 4000
PER_CLASS_TARGET = ENGLISH_SOURCE_ROWS // 14  # 285
EXTRA_ROWS = ENGLISH_SOURCE_ROWS - (PER_CLASS_TARGET * 14)  # remainder

# Level mix inside each class
LEVEL_RATIOS = {
    "primary": 0.46,
    "secondary": 0.33,
    "tertiary": 0.21,
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

# Whether final merged CSV should include the English source subset
INCLUDE_ENGLISH_IN_MERGED = False

# Filters
MIN_SCORE = 6.0
MIN_WORDS = 12
MAX_WORDS = 110
MIN_CHARS = 80
MAX_CHARS = 700
MAX_REPEAT_RATIO = 0.65

# Translation batching
BATCH_SIZE = 24 if DEVICE == "cuda" else 6
MAX_SOURCE_LENGTH = 256
MAX_TARGET_LENGTH = 256
NUM_BEAMS = 1

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

def per_level_targets(total_rows: int):
    p = round(total_rows * LEVEL_RATIOS["primary"])
    s = round(total_rows * LEVEL_RATIOS["secondary"])
    t = total_rows - p - s
    return {"primary": p, "secondary": s, "tertiary": t}

# =========================================================
# LOAD + FILTER
# =========================================================

def load_and_filter(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)

    required = ["text", "context_class", "relevance_level", "score"]
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")

    df["text"] = df["text"].apply(clean_text)
    df["context_class"] = df["context_class"].astype(str).str.strip().str.lower()
    df["relevance_level"] = df["relevance_level"].astype(str).str.strip().str.lower()
    df["score"] = pd.to_numeric(df["score"], errors="coerce").fillna(0.0)

    df["word_len"] = df["text"].apply(word_count)
    df["char_len"] = df["text"].apply(char_count)
    df["repeat_ratio"] = df["text"].apply(repetitive_ratio)

    df = df[df["context_class"].isin(CLASS_ORDER)].copy()
    df = df[df["relevance_level"].isin(["primary", "secondary", "tertiary"])].copy()
    df = df[df["score"] >= MIN_SCORE].copy()
    df = df[df["word_len"].between(MIN_WORDS, MAX_WORDS)].copy()
    df = df[df["char_len"].between(MIN_CHARS, MAX_CHARS)].copy()
    df = df[df["repeat_ratio"] <= MAX_REPEAT_RATIO].copy()

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

    df["selection_score"] = (
        df["score"] * 2.0 +
        df["level_weight"] * 3.0 +
        df["length_quality"] * 1.5 -
        (df["char_len"] / 1000.0)
    )

    return df.reset_index(drop=True)

# =========================================================
# SELECT 4K ENGLISH SOURCE SUBSET
# =========================================================

def select_english_4k(df: pd.DataFrame) -> pd.DataFrame:
    picked = []

    extra_classes = set(CLASS_ORDER[:EXTRA_ROWS])

    for cls in CLASS_ORDER:
        class_target = PER_CLASS_TARGET + (1 if cls in extra_classes else 0)
        level_targets = per_level_targets(class_target)

        cls_df = df[df["context_class"] == cls].copy()

        class_parts = []
        used_keys = set()

        for level in ["primary", "secondary", "tertiary"]:
            need = level_targets[level]
            sub = cls_df[cls_df["relevance_level"] == level].copy()
            sub = sub.sort_values(
                by=["selection_score", "score", "char_len"],
                ascending=[False, False, True]
            )
            sub = sub.head(need)
            class_parts.append(sub)
            for _, r in sub.iterrows():
                used_keys.add((r["text"], r["context_class"]))

        class_selected = pd.concat(class_parts, ignore_index=True)

        if len(class_selected) < class_target:
            missing = class_target - len(class_selected)
            remain = cls_df[
                ~cls_df.apply(lambda r: (r["text"], r["context_class"]) in used_keys, axis=1)
            ].copy()
            remain = remain.sort_values(
                by=["selection_score", "score", "char_len"],
                ascending=[False, False, True]
            )
            class_selected = pd.concat([class_selected, remain.head(missing)], ignore_index=True)

        picked.append(class_selected.head(class_target))

    out = pd.concat(picked, ignore_index=True)
    out = out.drop_duplicates(subset=["text", "context_class"]).reset_index(drop=True)

    if len(out) < ENGLISH_SOURCE_ROWS:
        selected_keys = set(zip(out["text"], out["context_class"]))
        remain = df[
            ~df.apply(lambda r: (r["text"], r["context_class"]) in selected_keys, axis=1)
        ].copy()
        remain = remain.sort_values(
            by=["selection_score", "score", "char_len"],
            ascending=[False, False, True]
        )
        out = pd.concat([out, remain.head(ENGLISH_SOURCE_ROWS - len(out))], ignore_index=True)

    out = out.head(ENGLISH_SOURCE_ROWS).copy()

    out["context_class"] = pd.Categorical(out["context_class"], CLASS_ORDER, ordered=True)
    out["relevance_level"] = pd.Categorical(
        out["relevance_level"], ["primary", "secondary", "tertiary"], ordered=True
    )

    out = out.sort_values(
        by=["context_class", "relevance_level", "selection_score"],
        ascending=[True, True, False]
    ).reset_index(drop=True)

    out["context_class"] = out["context_class"].astype(str)
    out["relevance_level"] = out["relevance_level"].astype(str)

    return out

# =========================================================
# SUMMARY
# =========================================================

def save_summary(df: pd.DataFrame, prefix: str):
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
# LOAD INDIC TRANS
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
def translate_batch(texts: List[str], tgt_lang: str, tokenizer, model, ip) -> List[str]:
    batch = ip.preprocess_batch(
        texts,
        src_lang="eng_Latn",
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

def translate_dataframe(df: pd.DataFrame, lang_code: str, tgt_lang_tag: str, tokenizer, model, ip) -> pd.DataFrame:
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

    return pd.concat(records, ignore_index=True)

# =========================================================
# MAIN
# =========================================================

def main():
    print("[INFO] Loading and filtering raw data...")
    raw_df = load_and_filter(INPUT_CSV)
    save_summary(raw_df, "raw_filtered")

    print(f"[INFO] Filtered pool rows: {len(raw_df)}")

    print("[INFO] Selecting 4k English source subset...")
    english_df = select_english_4k(raw_df)

    english_df["original_text"] = english_df["text"]
    english_df["lang"] = "en"
    english_df["source_type"] = "original_english"

    english_path = os.path.join(OUTPUT_DIR, "selected_english_4k.csv")
    english_df.to_csv(english_path, index=False, encoding="utf-8")
    save_summary(english_df, "selected_english_4k")

    print(f"[INFO] English rows selected: {len(english_df)}")
    print("\n[INFO] By class:")
    print(english_df["context_class"].value_counts().sort_index())
    print("\n[INFO] By level:")
    print(english_df["relevance_level"].value_counts().sort_index())

    tokenizer, model, ip = load_translation_stack()

    translated_frames = []

    for lang_code, tgt_lang_tag in TARGET_LANGS.items():
        print(f"\n[INFO] Translating to {lang_code} ...")
        translated_df = translate_dataframe(english_df, lang_code, tgt_lang_tag, tokenizer, model, ip)

        lang_path = os.path.join(OUTPUT_DIR, f"translated_{lang_code}_4k.csv")
        translated_df.to_csv(lang_path, index=False, encoding="utf-8")

        translated_frames.append(translated_df)

    if INCLUDE_ENGLISH_IN_MERGED:
        merged = pd.concat([english_df] + translated_frames, ignore_index=True)
        merged_name = "multilingual_dataset_24k_with_english.csv"
    else:
        merged = pd.concat(translated_frames, ignore_index=True)
        merged_name = "multilingual_dataset_20k_translated_only.csv"

    merged_path = os.path.join(OUTPUT_DIR, merged_name)
    merged.to_csv(merged_path, index=False, encoding="utf-8")

    manifest = {
        "input_csv": INPUT_CSV,
        "model_name": MODEL_NAME,
        "device": DEVICE,
        "english_source_rows": int(len(english_df)),
        "translated_rows_per_language": 4000,
        "languages": list(TARGET_LANGS.keys()),
        "translated_total_rows": 4000 * len(TARGET_LANGS),
        "include_english_in_merged": INCLUDE_ENGLISH_IN_MERGED,
        "merged_total_rows": int(len(merged)),
        "outputs": {
            "selected_english_4k": english_path,
            "merged": merged_path,
        },
    }

    with open(os.path.join(OUTPUT_DIR, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print("\n[SUCCESS] Done.")
    print(f"[INFO] English source subset: {english_path}")
    print(f"[INFO] Final merged dataset: {merged_path}")

if __name__ == "__main__":
    main()