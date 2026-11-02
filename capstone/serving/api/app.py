"""FastAPI service for the LLM-powered customer support system.

Run locally:
    uvicorn capstone.serving.api.app:app --reload --port 8000

Defaults to the deterministic mock provider so the service works offline. Set
LLM_PROVIDER=openai|anthropic|local to use a real provider (requires its SDK and
credentials).
"""
import os
import time
from typing import List, Optional

from fastapi import FastAPI
from pydantic import BaseModel, Field

from capstone.governance.pii import redact
from capstone.serving.llm.mock_provider import MockProvider
from capstone.serving.llm.providers import LLMRequest, ProviderType, registry
from capstone.serving.rag import FaqRetriever

app = FastAPI(title="Customer Support LLM API", version="1.0.0")

_retriever: Optional[FaqRetriever] = None
_provider = MockProvider(delay_ms=1)


def get_retriever() -> FaqRetriever:
    global _retriever
    if _retriever is None:
        _retriever = FaqRetriever()
    return _retriever


def get_provider():
    """Return the configured provider, falling back to the mock provider."""
    name = os.getenv("LLM_PROVIDER", "mock").lower()
    if name == "mock":
        return _provider
    try:
        return registry.get(ProviderType(name))
    except Exception:
        return _provider


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    customer_id: Optional[str] = None
    top_k: int = Field(3, ge=1, le=10)


class ChatResponse(BaseModel):
    response: str
    citations: List[str]
    provider: str
    latency_ms: float
    pii_redacted: bool = False


class ClassifyRequest(BaseModel):
    subject: str = ""
    body: str = Field(..., min_length=1, max_length=8000)


class ClassifyResponse(BaseModel):
    category: str
    priority: str
    confidence: float
    reasoning: str


@app.get("/health")
async def health():
    provider = get_provider()
    return {
        "status": "ok",
        "provider": provider.provider_type.value,
        "provider_healthy": await provider.health_check(),
        "faq_documents": len(get_retriever().documents),
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    started = time.perf_counter()
    safe_message = redact(request.message)
    retriever = get_retriever()
    context, citations = retriever.build_context(safe_message.text, top_k=request.top_k)

    prompt = safe_message.text
    if context:
        prompt = (
            "Answer the customer using only the knowledge base excerpts below. "
            "Cite excerpt ids in brackets.\n\n"
            f"{context}\n\nCustomer message: {safe_message.text}"
        )

    provider = get_provider()
    llm_response = await provider.generate(
        LLMRequest(prompt=prompt, system_prompt="You are a helpful support agent.")
    )
    fallback_text = retriever.retrieve(safe_message.text, top_k=1)
    response_text = llm_response.text
    if llm_response.provider == ProviderType.MOCK and fallback_text:
        response_text = fallback_text[0].text

    return ChatResponse(
        response=response_text,
        citations=citations,
        provider=llm_response.provider.value,
        latency_ms=round((time.perf_counter() - started) * 1000, 2),
        pii_redacted=safe_message.redacted,
    )


@app.post("/tickets/classify", response_model=ClassifyResponse)
async def classify(request: ClassifyRequest):
    text = f"{request.subject} {request.body}".strip().lower()
    rules = [
        ("billing", ("refund", "invoice", "payment", "charge", "declined", "plan")),
        ("account", ("password", "login", "two-factor", "2fa", "email", "sso")),
        ("bug_report", ("error", "crash", "bug", "broken", "fails")),
        ("technical", ("upload", "export", "api", "integration", "timeout")),
        ("feature_request", ("feature", "would like", "suggest", "request")),
    ]
    for category, keywords in rules:
        hits = sum(1 for kw in keywords if kw in text)
        if hits:
            confidence = min(0.95, 0.55 + 0.15 * hits)
            priority = "high" if any(w in text for w in ("urgent", "outage", "down", "critical")) else "medium"
            return ClassifyResponse(
                category=category,
                priority=priority,
                confidence=round(confidence, 2),
                reasoning=f"Matched {hits} keyword(s) for {category}.",
            )
    return ClassifyResponse(
        category="general",
        priority="low",
        confidence=0.35,
        reasoning="No category keywords matched; routed to general support.",
    )