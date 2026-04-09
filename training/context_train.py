import os
os.environ['KAGGLE_CONFIG_DIR'] = r'F:\fact_checking_system'

import kaggle
from torchaudio import datasets
import torch

# Example: List datasets using Kaggle API
api = kaggle.api
api.authenticate()
datasets = api.datasets_list()
for d in datasets[:10]:  # Show first 10 datasets
	print(f"{d.ref}: {d.title}")