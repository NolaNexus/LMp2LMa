"""Plugin interfaces for the capstone modular monolith (ADR-001)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from capstone.serving.rag import FaqRetriever, RetrievedDocument


@runtime_checkable
class RetrievalPlugin(Protocol):
    """Protocol every retrieval plugin must satisfy (ADR-001)."""

    name: str

    def retrieve(self, query: str, top_k: int = 3) -> list[RetrievedDocument]: ...


class FaqRetrievalPlugin:
    """Default retrieval plugin backed by the FAQ corpus."""

    name = "faq_retrieval"

    def __init__(self, retriever: FaqRetriever | None = None):
        self.retriever = retriever or FaqRetriever()

    def retrieve(self, query: str, top_k: int = 3) -> list[RetrievedDocument]:
        return self.retriever.retrieve(query, top_k=top_k)
