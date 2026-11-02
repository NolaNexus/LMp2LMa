"""
Local Model Provider (Ollama / vLLM compatible)
"""

import asyncio
import json
import os
import time
from typing import AsyncIterator, List

import httpx

from capstone.serving.llm.providers import (
    EmbeddingRequest,
    EmbeddingResponse,
    LLMProvider,
    LLMRequest,
    LLMResponse,
    ProviderType,
    registry,
)


class LocalProvider(LLMProvider):
    """Provider for local models via Ollama or vLLM (OpenAI-compatible API)"""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",  # Ollama default
        model: str = "llama3",
        embedding_model: str = "nomic-embed-text",
        timeout: float = 60.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.default_model = model
        self.embedding_model = embedding_model
        self.client = httpx.AsyncClient(timeout=timeout)
        self._models = [model, embedding_model]

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.LOCAL

    @property
    def default_model(self) -> str:
        return self._default_model

    @default_model.setter
    def default_model(self, value: str):
        self._default_model = value
        if value not in self._models:
            self._models.append(value)

    @property
    def supported_models(self) -> List[str]:
        return self._models

    async def generate(self, request: LLMRequest) -> LLMResponse:
        start = time.perf_counter()

        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})

        payload = {
            "model": request.metadata.get("model", self.default_model),
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": False,
        }

        if request.stop_sequences:
            payload["stop"] = request.stop_sequences

        response = await self.client.post(f"{self.base_url}/v1/chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()

        latency_ms = (time.perf_counter() - start) * 1000
        choice = data["choices"][0]

        return LLMResponse(
            text=choice["message"]["content"],
            provider=ProviderType.LOCAL,
            model=data["model"],
            tokens_used=data.get("usage", {}).get("total_tokens", 0),
            latency_ms=latency_ms,
            finish_reason=choice.get("finish_reason", "stop"),
            metadata=data.get("usage", {}),
        )

    async def generate_stream(self, request: LLMRequest) -> AsyncIterator[str]:
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})

        payload = {
            "model": request.metadata.get("model", self.default_model),
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": True,
        }

        if request.stop_sequences:
            payload["stop"] = request.stop_sequences

        async with self.client.stream(
            "POST", f"{self.base_url}/v1/chat/completions", json=payload
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk["choices"][0]["delta"]
                        if "content" in delta and delta["content"]:
                            yield delta["content"]
                    except json.JSONDecodeError:
                        continue

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        start = time.perf_counter()

        model = request.model or self.embedding_model
        payload = {"model": model, "input": request.texts}

        response = await self.client.post(f"{self.base_url}/v1/embeddings", json=payload)
        response.raise_for_status()
        data = response.json()

        latency_ms = (time.perf_counter() - start) * 1000

        return EmbeddingResponse(
            embeddings=[d["embedding"] for d in data["data"]],
            provider=ProviderType.LOCAL,
            model=model,
            tokens_used=data.get("usage", {}).get("total_tokens", 0),
            latency_ms=latency_ms,
        )

    async def health_check(self) -> bool:
        try:
            response = await self.client.get(f"{self.base_url}/v1/models", timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> List[str]:
        try:
            response = await self.client.get(f"{self.base_url}/v1/models")
            data = response.json()
            return [m["id"] for m in data.get("data", [])]
        except Exception:
            return []


# Register if local endpoint available
if os.getenv("LOCAL_LLM_URL"):
    try:
        provider = LocalProvider(base_url=os.getenv("LOCAL_LLM_URL"))
        if asyncio.run(provider.health_check()):
            registry.register(provider, is_primary=False)
    except Exception:
        pass
