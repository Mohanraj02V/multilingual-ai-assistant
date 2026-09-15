import json
import re
import math
import logging
from pathlib import Path
from typing import List, Dict, Any

from app.config import settings

logger = logging.getLogger(__name__)


class KnowledgeDocument:
    def __init__(self, id: str, title: str, content: str):
        self.id = id
        self.title = title
        self.content = content


class RetrievalService:
    """Simple keyword-based retrieval from knowledge.json.
    
    This is intentionally a thin, replaceable layer.
    To upgrade to vector search:
    1. Replace _compute_score() with embedding similarity
    2. Replace _load_documents() with DB connection
    3. Keep the retrieve() interface unchanged
    """

    def __init__(self):
        self._documents: List[KnowledgeDocument] = []
        self._load_documents()

    def _load_documents(self):
        """Load knowledge base from JSON file."""
        kb_path = Path(settings.knowledge_base_path)
        if not kb_path.exists():
            logger.warning(f"Knowledge base not found at {kb_path}")
            return

        with open(kb_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self._documents = [
            KnowledgeDocument(
                id=item["id"],
                title=item["title"],
                content=item["content"],
            )
            for item in data
        ]
        logger.info(f"Loaded {len(self._documents)} knowledge documents")

    def _tokenize(self, text: str) -> List[str]:
        """Lowercase, strip punctuation, split into tokens."""
        text = text.lower()
        text = re.sub(r"[^\w\s]", " ", text)
        return [t for t in text.split() if len(t) > 2]

    def _compute_score(self, query_tokens: List[str], doc: KnowledgeDocument) -> float:
        """TF-IDF-inspired simple scoring: count token overlap."""
        doc_text = f"{doc.title} {doc.content}".lower()
        doc_text = re.sub(r"[^\w\s]", " ", doc_text)
        doc_tokens = set(doc_text.split())

        if not query_tokens:
            return 0.0

        matches = sum(1 for token in query_tokens if token in doc_tokens)
        # Normalise by sqrt of query length to avoid penalising short queries too harshly
        score = matches / math.sqrt(len(query_tokens))
        return score

    def retrieve(
        self, query: str, top_k: int = None
    ) -> List[KnowledgeDocument]:
        """Return the top-k most relevant documents for the query.
        
        Args:
            query: The user's question (in English, after translation).
            top_k: Maximum number of documents to return.
            
        Returns:
            List of KnowledgeDocument sorted by relevance descending.
        """
        if top_k is None:
            top_k = settings.max_context_documents

        query_tokens = self._tokenize(query)

        scored = [
            (doc, self._compute_score(query_tokens, doc))
            for doc in self._documents
        ]

        # Filter by minimum score
        scored = [(doc, s) for doc, s in scored if s >= settings.retrieval_min_score]
        scored.sort(key=lambda x: x[1], reverse=True)

        return [doc for doc, _ in scored[:top_k]]

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
