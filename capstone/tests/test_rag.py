"""Unit tests for the capstone retrieval layer."""
from capstone.serving.rag import FaqRetriever, answer_with_retrieval


def test_retriever_returns_relevant_faq():
    retriever = FaqRetriever()
    results = retriever.retrieve("I forgot my password and cannot sign in", top_k=3)
    assert results, "expected at least one FAQ match"
    assert results[0].id == "FAQ-001"
    assert results[0].score > 0.05


def test_retriever_respects_top_k():
    retriever = FaqRetriever()
    results = retriever.retrieve("billing payment invoice", top_k=2)
    assert len(results) <= 2


def test_build_context_includes_citations():
    retriever = FaqRetriever()
    context, citations = retriever.build_context("How do I request a refund?")
    assert citations
    assert all(cid.startswith("FAQ-") for cid in citations)
    assert citations[0] in context


def test_unknown_query_yields_no_context():
    retriever = FaqRetriever()
    context, citations = retriever.build_context("zzzz unrelated gibberish xyzzy")
    assert context == ""
    assert citations == []


def test_answer_with_retrieval_returns_top_answer():
    retriever = FaqRetriever()
    answer, citations = answer_with_retrieval("payment declined", retriever)
    assert answer
    assert citations[0] == "FAQ-002"