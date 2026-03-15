import argparse
import json

import torch
import torch.nn.functional as F
from transformers import AutoModelForSequenceClassification, AutoTokenizer


LABEL_TO_DOMAIN = {
    'science': 'science',
    'health': 'health',
    'technology': 'technology',
    'history': 'history',
    'politics_government': 'politics_government',
    'economics_business': 'economics_business',
    'geography': 'geography',
    'space_astronomy': 'space_astronomy',
    'environment_climate': 'environment_climate',
    'society_culture': 'society_culture',
    'law_crime': 'law_crime',
    'sports': 'sports',
    'entertainment': 'entertainment',
    'general_factual': 'general_factual',
}


def main():
    parser = argparse.ArgumentParser(description='Isolated context inference helper.')
    parser.add_argument('--checkpoint', required=True)
    parser.add_argument('--device', default='cpu')
    parser.add_argument('--text', required=True)
    args = parser.parse_args()

    device = torch.device(args.device)
    tokenizer = AutoTokenizer.from_pretrained(args.checkpoint, use_fast=False)
    model = AutoModelForSequenceClassification.from_pretrained(args.checkpoint).to(device)
    model.eval()

    inputs = tokenizer(
        args.text,
        return_tensors='pt',
        truncation=True,
        max_length=256,
    ).to(device)

    with torch.no_grad():
        outputs = model(**inputs)
        probs = F.softmax(outputs.logits, dim=1)

    predicted = torch.argmax(probs, dim=1).item()
    raw_label = str(model.config.id2label.get(predicted, f'LABEL_{predicted}')).lower()
    label = LABEL_TO_DOMAIN.get(raw_label, 'general_factual')
    confidence = probs[0][predicted].item()
    scores = {
        str(model.config.id2label.get(idx, idx)).lower(): float(probs[0][idx].item())
        for idx in range(probs.shape[-1])
    }

    print(json.dumps({'label': label, 'confidence': float(confidence), 'scores': scores}))


if __name__ == '__main__':
    main()
