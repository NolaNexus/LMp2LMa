# ADR-002: LLM Provider Abstraction and Multi-Provider Strategy

**Status**: Accepted
**Date**: 2026-11-01
**Deciders**: ML Architect Team
**Technical Story**: Define how to abstract LLM providers for flexibility and cost optimization

## Context

The system needs to support multiple LLM providers:
- OpenAI (GPT-4, GPT-3.5-turbo)
- Anthropic (Claude 3 Opus/Sonnet/Haiku)
- Local models (Llama 3, Mistral, Phi-3 via Ollama/vLLM)
- Future providers (Gemini, Cohere, etc.)

Requirements:
- Runtime provider switching without redeployment
- Cost tracking per provider
- Fallback chains (primary → secondary → local)
- Prompt template compatibility across providers
- Token usage monitoring and budgeting

## Decision

We will implement a **Provider Abstraction Layer with Adapter Pattern**:

```
LLMClient (interface)
├── OpenAIAdapter
├── AnthropicAdapter
├── LocalModelAdapter (Ollama/vLLM)
└── MockAdapter (testing)
```

Key components:
1. **Unified Request/Response Schema**: Normalized across providers
2. **Provider Registry**: Dynamic registration with health checks
3. **Cost Calculator**: Per-provider token pricing with caching
4. **Routing Policy**: Configurable fallback chains and load balancing
5. **Prompt Template Engine**: Jinja2-based with provider-specific overrides

## Consequences

**Positive**:
- Zero-downtime provider switching
- Cost optimization via routing policies
- Easy to add new providers
- Testing with MockAdapter

**Negative**:
- Abstraction overhead (minimal)
- Provider-specific features may not map perfectly
- Prompt engineering per provider still needed

## Alternatives Considered

1. **Direct SDK usage**: Tight coupling, hard to switch
2. **LangChain/LlamaIndex**: Heavy dependencies, version conflicts
3. **Custom per-provider code**: Maintenance burden

## Implementation Notes

- `capstone/serving/llm/providers/` - adapter implementations
- `capstone/serving/llm/router.py` - routing and fallback logic
- `capstone/serving/llm/cost.py` - token tracking and budgeting
- Config: `capstone/config/llm_providers.yaml`
- Metrics: Prometheus counters for tokens, latency, errors per provider