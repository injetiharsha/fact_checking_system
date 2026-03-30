import argparse
import json
import sys

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


def _load_model(checkpoint, device_name):
    device = torch.device(device_name)
    tokenizer = AutoTokenizer.from_pretrained(checkpoint, use_fast=False)
    model = AutoModelForSequenceClassification.from_pretrained(checkpoint).to(device)
    model.eval()
    return device, tokenizer, model


def _predict(text, device, tokenizer, model):
    inputs = tokenizer(
        text,
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

    return {'label': label, 'confidence': float(confidence), 'scores': scores}


def main():
    parser = argparse.ArgumentParser(description='Isolated context inference helper.')
    parser.add_argument('--checkpoint', required=True)
    parser.add_argument('--device', default='cpu')
    parser.add_argument('--text', default=None)
    parser.add_argument('--serve', action='store_true')
    args = parser.parse_args()

    device, tokenizer, model = _load_model(args.checkpoint, args.device)

    if args.serve:
        print(json.dumps({'status': 'ready'}), flush=True)
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
                text = str(payload.get('text') or '')
                if not text:
                    print(json.dumps({'error': 'missing_text'}), flush=True)
                    continue
                print(json.dumps(_predict(text, device, tokenizer, model)), flush=True)
            except Exception as exc:
                print(json.dumps({'error': str(exc)}), flush=True)
        return

    if not args.text:
        raise SystemExit('--text is required unless --serve is used')

    print(json.dumps(_predict(args.text, device, tokenizer, model)))


if __name__ == '__main__':
    main()
