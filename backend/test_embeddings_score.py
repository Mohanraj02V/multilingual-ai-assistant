import json
import httpx
import math
import numpy as np
import time

def cosine_similarity(v1, v2):
    return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

def get_embedding(text):
    payload = {
        "model": "nomic-embed-text",
        "prompt": text,
        "keep_alive": "30m"
    }
    with httpx.Client(timeout=120) as client:
        start_time = time.time()
        response = client.post("http://localhost:11434/api/embeddings", json=payload)
        response.raise_for_status()
        latency = time.time() - start_time
        return response.json()["embedding"], latency

def main():
    with open('data/knowledge.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    print("Embedding documents...")
    doc_embeddings = {}
    total_doc_latency = 0
    for item in data:
        doc_text = f"{item['title']}\n{item['content']}"
        emb, lat = get_embedding(doc_text)
        doc_embeddings[item['id']] = emb
        total_doc_latency += lat
    print(f"Total time embedding docs: {total_doc_latency:.2f}s")
        
    queries = [
        # Known relevant (paraphrased)
        ("when do you guys close the shop?", "working-hours"),
        ("I need to speak to someone on the phone", "contact-information"),
        ("do you give my money back if I cancel?", "refund-policy"),
        # Known irrelevant
        ("what is the meaning of life?", None),
        ("how do I cook pasta?", None)
    ]
    
    print("\nTesting queries...")
    scores = []
    total_query_latency = 0
    for q, expected in queries:
        q_emb, lat = get_embedding(q)
        total_query_latency += lat
        best_doc = None
        best_score = -1
        
        print(f"\nQ: {q}")
        for doc_id, d_emb in doc_embeddings.items():
            sim = cosine_similarity(q_emb, d_emb)
            dist = 1 - sim
            print(f"  {doc_id}: dist={dist:.4f}")
            if sim > best_score:
                best_score = sim
                best_doc = doc_id
                
        dist_best = 1 - best_score
        scores.append(dist_best)
        print(f"=> Best match: {best_doc} (Distance: {dist_best:.4f}), Expected: {expected} | Latency: {lat:.2f}s")
        
    print(f"\nAverage query embedding latency: {total_query_latency/len(queries):.2f}s")
        
if __name__ == "__main__":
    main()
