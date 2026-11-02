"""
Mock Provider for Testing
"""
import time
import random
from typing import List, Dict, Any, AsyncIterator
from capstone.serving.llm.providers import (
    LLMProvider, ProviderType, LLMRequest, LLMResponse,
    EmbeddingRequest, EmbeddingResponse, registry
)


class MockProvider(LLMProvider):
    """Mock provider for testing and development"""

    def __init__(self, delay_ms: float = 100, error_rate: float = 0.0):
        self.delay_ms = delay_ms
        self.error_rate = error_rate
        self._models = ["mock-model", "mock-embedding"]

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.MOCK

    @property
    def default_model(self) -> str:
        return "mock-model"

    @property
    def supported_models(self) -> List[str]:
        return self._models

    async def generate(self, request: LLMRequest) -> LLMResponse:
        if random.random() < self.error_rate:
            raise RuntimeError("Mock provider simulated error")

        await asyncio.sleep(self.delay_ms / 1000)

        # Generate contextual response based on prompt
        prompt_lower = request.prompt.lower()
        if "classify" in prompt_lower or "category" in prompt_lower:
            text = json.dumps({
                "category": "technical",
                "confidence": 0.92,
                "priority": "medium",
                "reasoning": "Mock classification for testing"
            })
        elif "generate" in prompt_lower or "response" in prompt_lower:
            text = "Thank you for contacting support. I understand your issue and I'm here to help. Based on your description, this appears to be a technical issue that we can resolve. Let me provide you with some troubleshooting steps..."
        elif "escalate" in prompt_lower:
            text = json.dumps({
                "should_escalate": False,
                "reason": null,
                "confidence": 0.85,
                "reasoning": "Mock escalation decision"
            })
        else:
            text = "Mock response for: " + request.prompt[:50]

        return LLMResponse(
            text=text,
            provider=ProviderType.MOCK,
            model=self.default_model,
            tokens_used=len(text) // 4,
            latency_ms=self.delay_ms,
            finish_reason="stop",
            metadata={"mock": True}
        )

    async def generate_stream(self, request: LLMRequest) -> AsyncIterator[str]:
        response = await self.generate(request)
        # Simulate streaming by yielding chunks
        words = response.text.split()
        for i, word in enumerate(words):
            await asyncio.sleep(0.01)
            yield word + (" " if i < len(words) - 1 else "")

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        await asyncio.sleep(self.delay_ms / 1000)

        # Generate deterministic mock embeddings based on text hash
        embeddings = []
        for text in request.texts:
            # Simple hash-based embedding for reproducibility
            import hashlib
            hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
            embedding = [(hash_val >> i) & 1 for i in range(1536)]
            # Normalize
            norm = sum(x*x for x in embedding) ** 0.5
            embedding = [x / norm if norm > 0 else 0 for x in embedding]
            embeddings.append(embedding)

        return EmbeddingResponse(
            embeddings=embeddings,
            provider=ProviderType.MOCK,
            model="mock-embedding",
            tokens_used=sum(len(t) // 4 for t in request.texts),
            latency_ms=self.delay_ms
        )

    async def health_check(self) -> bool:
        return True


import asyncio
import json

# Auto-register mock for testing
registry.register(MockProvider(), is_primary=False)