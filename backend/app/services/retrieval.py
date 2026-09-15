import json
import logging
from pathlib import Path
from typing import List, Dict, Any
import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import settings
from app.services.llm.factory import get_llm_provider

logger = logging.getLogger(__name__)

class KnowledgeDocument:
    def __init__(self, id: str, title: str, content: str):
        self.id = id
        self.title = title
        self.content = content


class RetrievalService:
    """Semantic vector-based retrieval using ChromaDB and Ollama embeddings."""

    def __init__(self):
        self._documents: Dict[str, KnowledgeDocument] = {}
        # Enforce single-worker usage. PersistentClient is not safe for concurrent writers.
        self._chroma_client = chromadb.PersistentClient(path="./data/chroma")
        self._collection_name = "knowledge"
        self._llm = get_llm_provider()
        
    async def initialize(self):
        """Async initialization to load and embed documents."""
        await self._load_documents()

    async def _load_documents(self):
        """Load knowledge base, embed, and store in ChromaDB."""
        kb_path = Path(settings.knowledge_base_path)
        if not kb_path.exists():
            logger.warning(f"Knowledge base not found at {kb_path}")
            return

        with open(kb_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self._documents = {
            item["id"]: KnowledgeDocument(
                id=item["id"],
                title=item["title"],
                content=item["content"],
            )
            for item in data
        }
        
        # We wipe and recreate the collection to prevent orphaned chunks if docs were deleted/shrunk.
        try:
            self._chroma_client.delete_collection(self._collection_name)
        except Exception:
            pass # Collection does not exist yet

        # "cosine" space maps to 1 - cosine_similarity (0 = identical, 2 = opposite)
        collection = self._chroma_client.create_collection(
            name=self._collection_name, 
            metadata={"hnsw:space": "cosine"}
        )

        chunk_ids = []
        embeddings = []
        metadatas = []
        documents_text = []

        for doc_id, doc in self._documents.items():
            full_text = f"{doc.title}\n{doc.content}"
            
            # Simple chunking if document is long
            if len(full_text) > 500:
                chunks = self._chunk_text(full_text, chunk_size=500, overlap=50)
            else:
                chunks = [full_text]
                
            for i, chunk in enumerate(chunks):
                # We need to await the embedding generation
                emb = await self._llm.generate_embeddings(chunk)
                
                chunk_ids.append(f"{doc_id}_{i}")
                embeddings.append(emb)
                metadatas.append({"doc_id": doc_id})
                documents_text.append(chunk)

        if chunk_ids:
            collection.add(
                ids=chunk_ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=documents_text
            )
            
        logger.info(f"Loaded {len(self._documents)} documents and created {len(chunk_ids)} embedded chunks in ChromaDB")

    def _chunk_text(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        """Split text into overlapping chunks."""
        chunks = []
        start = 0
        text_len = len(text)
        while start < text_len:
            end = min(start + chunk_size, text_len)
            chunks.append(text[start:end])
            if end == text_len:
                break
            start += chunk_size - overlap
        return chunks

    async def retrieve(
        self, query: str, top_k: int = None
    ) -> List[KnowledgeDocument]:
        """Return the top-k most relevant documents for the query via vector search."""
        if top_k is None:
            top_k = settings.max_context_documents

        try:
            collection = self._chroma_client.get_collection(self._collection_name)
        except Exception: # Catch NotFoundError or ValueError
            return []
            
        query_emb = await self._llm.generate_embeddings(query)
        if not query_emb:
            return []

        results = collection.query(
            query_embeddings=[query_emb],
            n_results=top_k * 2  # Oversample slightly to handle chunk deduplication
        )
        
        if not results['ids'] or not results['ids'][0]:
            return []
            
        retrieved_docs = []
        seen_doc_ids = set()
        
        distances = results['distances'][0]
        metadatas = results['metadatas'][0]
        
        for distance, metadata in zip(distances, metadatas):
            # distance is 1 - cosine_similarity. So lower is better.
            # We need to test empirical threshold, using retrieval_min_score which we will tune.
            if distance <= settings.retrieval_min_score:
                doc_id = metadata["doc_id"]
                if doc_id not in seen_doc_ids:
                    if doc_id in self._documents:
                        retrieved_docs.append(self._documents[doc_id])
                        seen_doc_ids.add(doc_id)
                        
            if len(retrieved_docs) >= top_k:
                break
                
        return retrieved_docs

    def format_context(self, documents: List[KnowledgeDocument]) -> str:
        """Format retrieved documents as a LLM-readable context block."""
        if not documents:
            return ""

        parts = []
        for doc in documents:
            parts.append(f"[{doc.title}]\n{doc.content}")

        return "\n\n---\n\n".join(parts)


# Singleton instance
retrieval_service = RetrievalService()
