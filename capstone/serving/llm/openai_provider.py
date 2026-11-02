"""
OpenAI Provider Implementation
"""
import os
import time
from typing import List, Dict, Any, AsyncIterator
from capstone.serving.llm.providers import (
    LLMProvider, ProviderType, LLMRequest, LLMResponse,
    EmbeddingRequest, EmbeddingResponse, registry
)

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    openai = None


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: Optional[str] = None, organization: Optional[str] = None):
        if not OPENAI_AVAILABLE:
            raise RuntimeError("openai package not installed. Run: pip install openai")

        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key required")

        self.client = openai.AsyncOpenAI(api_key=self.api_key, organization=organization)
        self._models = [
            "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4",
            "gpt-3.5-turbo", "gpt-3.5-turbo-16k",
            "text-embedding-3-large", "text-embedding-3-small", "text-embedding-ada-002"
        ]

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.OPENAI

    @property
    def default_model(self) -> str:
        return "gpt-4o-mini"

    @property
    def supported_models(self) -> List[str]:
        return self._models

    async def generate(self, request: LLMRequest) -> LLMResponse:
        start = time.perf_counter()

        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})

        response = await self.client.chat.completions.create(
            model=request.metadata.get("model", self.default_model),
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stop=request.stop_sequences or None,
        )

        latency_ms = (time.perf_counter() - start) * 1000
        choice = response.choices[0]

        return LLMResponse(
            text=choice.message.content or "",
            provider=ProviderType.OPENAI,
            model=response.model,
            tokens_used=response.usage.total_tokens if response.usage else 0,
            latency_ms=latency_ms,
            finish_reason=choice.finish_reason or "stop",
            metadata={"prompt_tokens": response.usage.prompt_tokens if response.usage else 0}
        )

    async def generate_stream(self, request: LLMRequest) -> AsyncIterator[str]:
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})

        stream = await self.client.chat.completions.create(
            model=request.metadata.get("model", self.default_model),
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stop=request.stop_sequences or None,
            stream=True,
        )

        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        start = time.perf_counter()

        model = request.model or "text-embedding-3-small"
        response = await self.client.embeddings.create(
            model=model,
            input=request.texts,
        )

        latency_ms = (time.perf_counter() - start) * 1000

        return EmbeddingResponse(
            embeddings=[d.embedding for d in response.data],
            provider=ProviderType.OPENAI,
            model=model,
            tokens_used=response.usage.total_tokens if response.usage else 0,
            latency_ms=latency_ms
        )

    async def health_check(self) -> bool:
        try:
            await self.client.models.list()
            return True
        except Exception:
            return False


# Register if available
if OPENAI_AVAILABLE and os.getenv("OPENAI_API_KEY"):
    try:
        registry.register(OpenAIProvider(), is_primary=True)
    except Exception:
        pass