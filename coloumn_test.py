from datasets import get_dataset_config_names, load_dataset

# Choose your language code (e.g., 'hi' for Hindi)
lang_code = 'hi'

# Get all configs for IndicGLUE
all_configs = get_dataset_config_names("ai4bharat/indic_glue")

# Filter configs for the chosen language
lang_configs = [cfg for cfg in all_configs if cfg.endswith(f".{hi}")]

print(f"All IndicGLUE configs for language '{lang_code}':")
for cfg in lang_configs:
    print(f"\nConfig: {cfg}")
    ds = load_dataset("ai4bharat/indic_glue", cfg)
    print("Columns:", ds['train'].column_names)
    print("Sample:", ds['train'][0])