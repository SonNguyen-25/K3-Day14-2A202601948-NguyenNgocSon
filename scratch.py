import json

with open('artifacts/actual_answers.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

for a in d['answers']:
    if a['id'] in ['A01', 'A02', 'A03', 'H04']:
        print(f"\nID: {a['id']}")
        print(f"Q: {a['question']}")
        print(f"Actual: {a['actual_answer']}")
        print("Expected:", [qa for qa in json.load(open('golden_dataset.json', encoding='utf-8'))['qa_pairs'] if qa['id'] == a['id']][0]['expected_answer'])

