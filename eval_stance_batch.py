import csv

def evaluate_stance_batch(input_csv, output_csv):
    gold = {}
    with open(input_csv, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = (row['premise'].strip(), row['hypothesis'].strip())
            gold[key] = row['label'].strip().upper()

    preds = {}
    with open(output_csv, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = (row['premise'].strip(), row['hypothesis'].strip())
            preds[key] = row['prediction'].strip().upper()

    total = len(gold)
    correct = 0
    failed = []
    for k in gold:
        if k in preds and preds[k] == gold[k]:
            correct += 1
        else:
            failed.append({
                'premise': k[0],
                'hypothesis': k[1],
                'gold': gold[k],
                'predicted': preds.get(k, 'MISSING')
            })
    accuracy = correct / total if total > 0 else 0
    print(f"Accuracy: {accuracy:.2%} ({correct}/{total})")
    if failed:
        print("\nFailed claims:")
        for f in failed:
            print(f"Premise: {f['premise']} | Hypothesis: {f['hypothesis']} | Gold: {f['gold']} | Predicted: {f['predicted']}")
    else:
        print("All claims predicted correctly!")

if __name__ == "__main__":
    evaluate_stance_batch("stance_batch_input.csv", "stance_batch_output.csv")
