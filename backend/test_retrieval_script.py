import json
import re
import math
from collections import Counter

with open('data/knowledge.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

def tokenize(text):
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    return [t for t in text.split() if len(t) > 2]

queries = [
    'what are your working hours',
    'how can i contact support',
    'what is your refund policy',
    'do you offer a free trial',
    'what are the shipping times',
    'can i change my password',
    'where is the company located'
]

print('--- OLD SCORING (Set intersection) ---')
for q in queries:
    qt = tokenize(q)
    scored = []
    for item in data:
        dt = set(tokenize(f"{item['title']} {item['content']}"))
        matches = sum(1 for t in qt if t in dt)
        score = matches / math.sqrt(len(qt)) if qt else 0
        scored.append((item['id'], score))
    scored.sort(key=lambda x: x[1], reverse=True)
    print(f"Q: {q:30} Top 3: {[f'{x[0]} ({x[1]:.2f})' for x in scored[:3]]}")

print('\n--- NEW SCORING (TF-IDF inspired term frequency) ---')
for q in queries:
    qt = tokenize(q)
    scored = []
    for item in data:
        dt = tokenize(f"{item['title']} {item['content']}")
        dt_counts = Counter(dt)
        # Simple TF: sum of term frequencies in document
        matches = sum(dt_counts[t] for t in qt)
        score = matches / math.sqrt(len(qt)) if qt else 0
        scored.append((item['id'], score))
    scored.sort(key=lambda x: x[1], reverse=True)
    print(f"Q: {q:30} Top 3: {[f'{x[0]} ({x[1]:.2f})' for x in scored[:3]]}")
