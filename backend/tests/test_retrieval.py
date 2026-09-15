import pytest
from app.services.retrieval import RetrievalService, KnowledgeDocument
from app.config import settings

@pytest.mark.asyncio
async def test_retrieval_format_context():
    service = RetrievalService()
    docs = [
        KnowledgeDocument(id="doc1", title="Title 1", content="Content 1"),
        KnowledgeDocument(id="doc2", title="Title 2", content="Content 2")
    ]
    context = service.format_context(docs)
    assert "[Title 1]" in context
    assert "Content 1" in context
    assert "[Title 2]" in context
    assert "Content 2" in context
