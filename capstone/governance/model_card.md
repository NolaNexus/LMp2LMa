# Model Card — Customer Support Assistant

## Model Details
- **Name**: customer-support-assistant
- **Version**: 1.0.0
- **Owner**: ML Architect Journey capstone
- **Type**: Retrieval-augmented generation (TF-IDF retriever + pluggable LLM)
- **Default runtime**: `MockProvider` (deterministic, offline)
- **Optional providers**: OpenAI, Anthropic, local (see ADR-002)
- **Languages**: English

## Intended Use
- Draft answers to common customer support questions using a curated FAQ corpus.
- Suggest a ticket category and priority from free-text subject and body.
- Provide citation ids so agents can verify each answer against the knowledge base.

## Out of Scope
- Autonomous resolution of billing disputes, refunds, or account deletion.
- Legal, medical, or financial advice.
- Non-English conversations.
- Processing of regulated personal data beyond transient redaction.

## Training Data
No model training occurs in this system. The retriever is fit at start-up on
`capstone/data/raw/faqs.json`. If a fine-tuned provider is used, its training
data provenance is owned by that provider and must be recorded in a separate
model card.

## Evaluation
- Contract tests: `python -m pytest capstone/tests -q`
- Grounding check: every `/chat` response must carry citations from the FAQ corpus.
- Latency and error SLOs: see `capstone/docs/operations.md`.
- Drift: `capstone.monitoring.metrics.DriftDetector` compares recent query
  embeddings to a reference centroid.

## Limitations
- Retrieval is lexical (TF-IDF). Paraphrases with no shared vocabulary may miss
  the correct FAQ entry.
- The fallback answer is the nearest FAQ answer; it is not generated and may not
  directly address multi-part questions.
- Classification is keyword-based and will route novel intents to `general`.
- No persistent conversation memory across requests.

## Ethical Considerations and Guardrails
- Inbound text is redacted for email, phone, credit card, SSN, and IPv4 before
  retrieval, logging, or provider calls (`capstone/governance/pii.py`).
- Answers are constrained to retrieved excerpts; unsupported claims should be
  escalated rather than generated.
- Low-confidence classifications are surfaced with `confidence` so the UI can
  route to a human.

## Governance
- PII redaction counts are reported on `/chat` as `pii_redacted`.
- Audit trail: request metrics are recorded by `MetricsCollector`; production
  deployments must forward them to the observability stack (ADR-005).
- Retraining/refresh trigger: FAQ corpus edits or sustained drift alerts.

## Contact
Open an issue in this repository with the `governance` label.
