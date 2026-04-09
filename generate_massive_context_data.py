import pandas as pd
import re
import random

# --- CONFIG ---
# List of 14 context classes
CONTEXT_CLASSES = [
    'science', 'health', 'technology', 'history', 'politics_government', 'economics_business',
    'geography', 'space_astronomy', 'environment_climate', 'society_culture', 'law_crime',
    'sports', 'entertainment', 'general_factual'
]

# Opinion/subjective patterns
OPINION_PATTERNS = [
    r'\bI am\b', r'\bI think\b', r'\bI believe\b', r'\bmy\b', r'\bme\b', r'\bwe\b', r'\bour\b',
    r'\bin my opinion\b', r'\bI feel\b', r'\bI guess\b', r'\bI suppose\b', r'\bI wish\b', r'\bI hope\b',
    r'\bI want\b', r'\bI like\b', r'\bI dislike\b', r'\bI hate\b', r'\bI love\b', r'\bI prefer\b',
    r'\bI suggest\b', r'\bI recommend\b', r'\bI would\b', r'\bI could\b', r'\bI should\b', r'\bI might\b',
    r'\bI wish\b', r'\bI hope\b', r'\bI guess\b', r'\bI suppose\b', r'\bI feel\b', r'\bI doubt\b',
    r'\bI wonder\b', r'\bI assume\b', r'\bI estimate\b', r'\bI expect\b', r'\bI predict\b', r'\bI suspect\b',
    r'\bI imagine\b', r'\bI sense\b', r'\bI sense\b', r'\bI sense\b', r'\bI sense\b', r'\bI sense\b'
]

# --- 1. DATA GENERATION ---
def generate_synthetic_data(num_per_class=1000, min_len=6, max_len=25, multi_label_ratio=0.1):
    """
    Generate synthetic data for all context classes.
    - num_per_class: Number of samples per class
    - min_len, max_len: Range of token lengths
    - multi_label_ratio: Fraction of samples with multiple labels
    """
    import faker
    fake = faker.Faker()
    data = []
    for label in CONTEXT_CLASSES:
        for _ in range(num_per_class):
            # Random sentence length
            sent_len = random.randint(min_len, max_len)
            # Generate a sentence
            sent = fake.sentence(nb_words=sent_len)
            # Multi-label
            if random.random() < multi_label_ratio:
                other_label = random.choice([l for l in CONTEXT_CLASSES if l != label])
                label_str = f"{label};{other_label}"
            else:
                label_str = label
            data.append({
                'claim': sent,
                'source': '',
                'label': label_str
            })
    df = pd.DataFrame(data)
    return df

# --- 2. FILTERING / CLEANSING ---
def filter_cleanse(df, min_words=5, max_words=30):
    # Remove questions
    df = df[~df['claim'].str.strip().str.endswith('?')]
    # Remove short/long lines
    df = df[df['claim'].str.split().apply(len).between(min_words, max_words)]
    # Remove opinions
    pattern = re.compile('|'.join(OPINION_PATTERNS), re.IGNORECASE)
    df = df[~df['claim'].str.contains(pattern)]
    return df.reset_index(drop=True)

# --- 3. BALANCE LENGTH & LABELS ---
def balance_length_and_labels(df, per_label=1000):
    # For each label, sample per_label examples with diverse lengths
    balanced = []
    for label in CONTEXT_CLASSES:
        # Support multi-label rows
        label_mask = df['label'].apply(lambda x: label in x.split(';'))
        sub = df[label_mask]
        # Sort by length
        sub['len'] = sub['claim'].str.split().apply(len)
        # Bin by length
        bins = pd.qcut(sub['len'], 5, duplicates='drop')
        for b in bins.unique():
            bin_sub = sub[sub['len'].between(b.left, b.right, inclusive='both')]
            n = per_label // len(bins.unique())
            balanced.append(bin_sub.sample(min(n, len(bin_sub)), random_state=42))
    return pd.concat(balanced).drop(columns=['len']).reset_index(drop=True)

# --- MAIN PIPELINE ---
if __name__ == "__main__":
    # 1. Generate
    df = generate_synthetic_data(num_per_class=2000, min_len=6, max_len=25, multi_label_ratio=0.15)
    # 2. Filter
    df = filter_cleanse(df, min_words=6, max_words=25)
    # 3. Balance
    df = balance_length_and_labels(df, per_label=2000)
    # 4. Save
    df.to_csv('context_labeled_data_massive.csv', index=False)
    print(f"Generated and cleaned dataset with {len(df)} rows. Saved as context_labeled_data_massive.csv")
