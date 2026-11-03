"""
Anthropic Provider Implementation
"""

import os
import time
from typing import AsyncIterator, List, Optional

from capstone.serving.llm.providers import (
    EmbeddingRequest,
    EmbeddingResponse,
    LLMProvider,
    LLMRequest,
    LLMResponse,
    ProviderType,
    registry,
)

try:
    import anthropic

    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    anthropic = None


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: Optional[str] = None):
        if not ANTHROPIC_AVAILABLE:
            raise RuntimeError("anthropic package not installed. Run: pip install anthropic")

        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Anthropic API key required")

        self.client = anthropic.AsyncAnthropic(api_key=self.api_key)
        self._models = [
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
            "claude-3-5-sonnet-20241022",
        ]

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.ANTHROPIC

    @property
    def default_model(self) -> str:
        return "claude-3-haiku-20240307"

    @property
    def supported_models(self) -> List[str]:
        return self._models

    async def generate(self, request: LLMRequest) -> LLMResponse:
        start = time.perf_counter()

        messages = []
        if request.system_prompt:
            # Anthropic uses system parameter, not system message
            pass  # We'll pass it separately

        messages.append({"role": "user", "content": request.prompt})

        response = await self.client.messages.create(
            model=request.metadata.get("model", self.default_model),
            system=request.system_prompt,
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stop_sequences=request.stop_sequences or None,
        )

        latency_ms = (time.perf_counter() - start) * 1000

        return LLMResponse(
            text=response.content[0].text if response.content else "",
            provider=ProviderType.ANTHROPIC,
            model=response.model,
            tokens_used=response.usage.input_tokens + response.usage.output_tokens,
            latency_ms=latency_ms,
            finish_reason=response.stop_reason or "stop",
            metadata={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
        )

    async def generate_stream(self, request: LLMRequest) -> AsyncIterator[str]:
        messages = [{"role": "user", "content": request.prompt}]

        stream = await self.client.messages.create(
            model=request.metadata.get("model", self.default_model),
            system=request.system_prompt,
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stop_sequences=request.stop_sequences or None,
            stream=True,
        )

        async for chunk in stream:
            if chunk.type == "content_block_delta" and chunk.delta.text:
                yield chunk.delta.text

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        # Anthropic doesn't provide embeddings API yet
        # Return mock embeddings for compatibility
        return EmbeddingResponse(
            embeddings=[[0.0] * 1536 for _ in request.texts],
            provider=ProviderType.ANTHROPIC,
            model="none",
            tokens_used=0,
            latency_ms=0,
        )

    async def health_check(self) -> bool:
        try:
            # Simple API call to verify connectivity
            await self.client.messages.create(
                model=self.default_model,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1,
            )
            return True
        except Exception:
            return False


if ANTHROPIC_AVAILABLE and os.getenv("ANTHROPIC_API_KEY"):
    try:
        registry.register(AnthropicProvider(), is_primary=False)
    except Exception:
        pass
