# System Architecture — LLM Customer Support

## 1. Overview

A modular monolith that classifies support tickets, retrieves grounded knowledge,
and drafts customer replies with an LLM. It is deployable as one container while
keeping module boundaries that allow extraction into services later (ADR-001).

```
            +-----------------------------+
 Customer ->|  API (FastAPI)              |
            |  /chat  /tickets/classify   |
            +------+-----------+----------+
                   |           |
         +---------v--+   +----v-----------------+
         | Retrieval  |   | LLM Provider Layer   |
         | (TF-IDF)   |   | mock/openai/anthropic|
         +-----+------+   | /local + fallback    |
               |          +----+-----------------+
        +------v------+        |
        | FAQ corpus  |   +----v-----------+
        | data/raw    |   | Monitoring     |
        +-------------+   | metrics/drift  |
                          +----------------+
```

## 2. Components

| Component | Module | Responsibility |
|---|---|---|
| Domain model | `capstone/serving/domain.py` | Tickets, messages, classifications, escalation, domain events |
| Provider abstraction | `capstone/serving/llm/providers.py` | Uniform async interface, registry, fallback chain |
| Providers | `capstone/serving/llm/*_provider.py` | OpenAI, Anthropic, local, deterministic mock |
| Retrieval | `capstone/serving/rag.py` | TF-IDF retrieval over `capstone/data/raw/faqs.json`, citation ids |
| API | `capstone/serving/api/app.py` | `/health`, `/chat`, `/tickets/classify` |
| Monitoring | `capstone/monitoring/metrics.py` | Latency/token/error metrics, p50/p95/p99, embedding drift |
| Infrastructure | `capstone/infrastructure/` | Docker image, Helm chart, Terraform module |

## 3. Request Flows

**Chat (RAG):**
1. Validate request (`ChatRequest`), enforce length limits.
2. Retrieve top-k FAQ excerpts and build a citation-bearing prompt.
3. Call the configured provider through the registry (mock by default).
4. For the mock provider, return the top retrieved answer so offline demos are
   deterministic; real providers return the generated text.
5. Record latency/tokens and return response with citations.

**Classification:**
1. Normalise subject + body.
2. Keyword scorer maps to `billing | account | bug_report | technical | feature_request | general`.
3. Escalate priority on urgency keywords (`urgent`, `outage`, `down`, `critical`).
4. Low-confidence results (`general`) route to human triage.

## 4. Non-Functional Requirements

| Attribute | Target | Implementation |
|---|---|---|
| Availability | 99.9% monthly (Enterprise) | 2+ replicas, HPA, readiness on `/health` |
| Latency | p95 < 2 s | Timeout budgets, mock fast path, p95 alert in `MetricsCollector` |
| Safety | No ungrounded answers | Retrieval-first prompt, citations, refusal on empty context |
| Cost | Bounded tokens | `max_tokens`, mock default in CI |
| Security | Least privilege | Non-root container user, no secrets in image, provider keys via env |
| Observability | Traceable decisions | Metrics collector, drift detector, structured provider metadata |

## 5. Deployment Topology

- **Container:** `capstone/infrastructure/Dockerfile`, non-root `appuser`, healthcheck on `/health`.
- **Helm:** `customer-support` chart with probes, resource requests/limits, optional HPA.
- **Terraform:** namespace + Helm release, provider validated to `mock|openai|anthropic|local`.

## 6. Tradeoffs

| Decision | Alternative | Why chosen |
|---|---|---|
| TF-IDF retrieval | Vector DB + embeddings | Zero infra, deterministic tests; swap point isolated in `FaqRetriever` |
| Mock provider default | Always-live provider | CI and demos run offline without keys |
| Modular monolith | Microservices | Faster iteration, fewer failure modes before scale demands it |
| Keyword classifier | LLM classifier | Cheap, explainable; LLM path available through the provider layer |

## 7. Related Decisions

- [ADR-001](adr-001-architecture-style.md) — modular monolith with plugins
- [ADR-002](adr-002-llm-provider-abstraction.md) — provider abstraction
- [ADR-003](adr-003-data-storage.md) — data storage
- [ADR-004](adr-004-deployment.md) — deployment
- [ADR-005](adr-005-observability.md) — observability

## 8. Extension Points

- Replace `FaqRetriever` with an embedding store; keep `build_context` contract.
- Add a cell mapping to checkpoints so the grader can score drill answers precisely.
- Extract `monitoring/` into a sidecar exporter (Prometheus format) when moving beyond a demo.
