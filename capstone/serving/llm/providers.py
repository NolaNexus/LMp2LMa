"""
LLM Provider Abstraction Layer
Supports OpenAI, Anthropic, Local (Ollama/vLLM), and Mock providers
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, AsyncIterator, Dict, List, Optional


class ProviderType(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"
    MOCK = "mock"


@dataclass
class LLMRequest:
    prompt: str
    system_prompt: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 1024
    stop_sequences: List[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.stop_sequences is None:
            self.stop_sequences = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class LLMResponse:
    text: str
    provider: ProviderType
    model: str
    tokens_used: int
    latency_ms: float
    finish_reason: str = "stop"
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class EmbeddingRequest:
    texts: List[str]
    model: Optional[str] = None


@dataclass
class EmbeddingResponse:
    embeddings: List[List[float]]
    provider: ProviderType
    model: str
    tokens_used: int
    latency_ms: float


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""

    @property
    @abstractmethod
    def provider_type(self) -> ProviderType:
        pass

    @property
    @abstractmethod
    def default_model(self) -> str:
        pass

    @property
    @abstractmethod
    def supported_models(self) -> List[str]:
        pass

    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        pass

    @abstractmethod
    async def generate_stream(self, request: LLMRequest) -> AsyncIterator[str]:
        pass

    @abstractmethod
    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        pass

    def estimate_tokens(self, text: str) -> int:
        """Rough token estimation (4 chars ≈ 1 token)"""
        return len(text) // 4


class ProviderRegistry:
    """Registry for dynamic provider management"""

    def __init__(self):
        self._providers: Dict[ProviderType, LLMProvider] = {}
        self._primary: Optional[ProviderType] = None
        self._fallback_chain: List[ProviderType] = []

    def register(self, provider: LLMProvider, is_primary: bool = False):
        self._providers[provider.provider_type] = provider
        if is_primary or self._primary is None:
            self._primary = provider.provider_type

    def set_fallback_chain(self, chain: List[ProviderType]):
        self._fallback_chain = chain

    def get(self, provider_type: Optional[ProviderType] = None) -> LLMProvider:
        if provider_type:
            return self._providers[provider_type]
        if self._primary:
            return self._providers[self._primary]
        raise ValueError("No provider available")

    async def generate_with_fallback(self, request: LLMRequest) -> LLMResponse:
        """Try primary, then fallback chain"""
        providers_to_try = [self._primary] + self._fallback_chain
        last_error = None

        for ptype in providers_to_try:
            if ptype not in self._providers:
                continue
            try:
                provider = self._providers[ptype]
                if await provider.health_check():
                    return await provider.generate(request)
            except Exception as e:
                last_error = e
                continue

        raise RuntimeError(f"All providers failed. Last error: {last_error}")


# Global registry instance
registry = ProviderRegistry()
