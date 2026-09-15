import asyncio
from app.services.retrieval import retrieval_service
from app.services.llm.factory import get_llm_provider

async def main():
    await retrieval_service.initialize()
    
    queries = ["tell me about the company", "thirumba Perumal Kovil Enna"]
    
    for query in queries:
        print(f"\nQuery: '{query}'")
        docs = await retrieval_service.retrieve(query, top_k=5)
        if docs:
            for doc in docs:
                print(f"  Matched: {doc.id}")
        else:
            print("  No documents matched within threshold.")
            
        # Let's bypass threshold to see actual distance
        query_emb = await get_llm_provider().generate_embeddings(query)
        collection = retrieval_service._chroma_client.get_collection(retrieval_service._collection_name)
        results = collection.query(query_embeddings=[query_emb], n_results=3)
        for doc_id, dist in zip(results["ids"][0], results["distances"][0]):
            print(f"    Raw: {doc_id}, dist={dist:.4f}")

if __name__ == "__main__":
    asyncio.run(main())
