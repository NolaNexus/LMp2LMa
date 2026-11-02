"""Retrieval-augmented generation over the customer-support FAQ corpus.

Uses TF-IDF + cosine similarity so the pipeline runs offline with no model
downloads. Swap `FaqRetriever` for an embedding-backed implementation without
changing the API surface.
"""
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

DEFAULT_CORPUS = Path(__file__).resolve().parent.parent / "data" / "raw" / "faqs.json"


@dataclass
class RetrievedDocument:
    id: str
    text: str
    score: float
    metadata: dict = field(default_factory=dict)


class FaqRetriever:
    """Dense-free retriever over structured FAQ entries."""

    def __init__(self, corpus_path: Optional[Path] = None):
        self.corpus_path = Path(corpus_path) if corpus_path else DEFAULT_CORPUS
        self.documents = json.loads(self.corpus_path.read_text())
        corpus = [f"{d['question']} {d['answer']}" for d in self.documents]
        self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        self.matrix = self.vectorizer.fit_transform(corpus)

    def retrieve(self, query: str, top_k: int = 3, min_score: float = 0.05) -> List[RetrievedDocument]:
        query_vec = self.vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self.matrix).ravel()
        ranked = np.argsort(scores)[::-1][:top_k]
        results = []
        for idx in ranked:
            score = float(scores[idx])
            if score < min_score:
                continue
            doc = self.documents[int(idx)]
            results.append(
                RetrievedDocument(
                    id=doc["id"],
                    text=doc["answer"],
                    score=score,
                    metadata={"question": doc["question"], "category": doc["category"]},
                )
            )
        return results

    def build_context(self, query: str, top_k: int = 3) -> tuple[str, List[str]]:
        """Return (context block, citation ids) for prompt construction."""
        retrieved = self.retrieve(query, top_k=top_k)
        if not retrieved:
            return "", []
        blocks = [f"[{doc.id}] {doc.metadata['question']}\n{doc.text}" for doc in retrieved]
        return "\n\n".join(blocks), [doc.id for doc in retrieved]


def answer_with_retrieval(query: str, retriever: FaqRetriever, top_k: int = 3) -> tuple[str, List[str]]:
    """Deterministic fallback answer built directly from retrieved FAQs."""
    retrieved = retriever.retrieve(query, top_k=top_k)
    if not retrieved:
        return "", []
    answer = retrieved[0].text
    return answer, [doc.id for doc in retrieved]