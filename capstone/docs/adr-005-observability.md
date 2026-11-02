# ADR-005: Observability - OpenTelemetry + Prometheus + Grafana + Loki

**Status**: Accepted
**Date**: 2026-11-01
**Deciders**: ML Architect Team
**Technical Story**: Define observability stack for the customer support system

## Context

Observability requirements:
- **Metrics**: Latency (p50/p95/p99), throughput, error rates, queue depths, LLM token usage, costs
- **Logs**: Structured JSON logs, correlation IDs, audit trail
- **Traces**: End-to-end request flow (API → classification → generation → response)
- **Business Metrics**: Classification accuracy, escalation rate, customer satisfaction, resolution time
- **Alerting**: SLO-based (latency <500ms p99, error rate <0.1%, availability >99.9%)
- **Debugging**: Live tailing, trace inspection, log correlation

Scale: ~10K RPS peak, ~1B events/day

## Decision

**OpenTelemetry-native stack**:

```
Applications → OTel Collector → Prometheus (metrics) + Tempo (traces) + Loki (logs)
                                                      ↓
                                              Grafana (visualization)
                                                      ↓
                                              Alertmanager + PagerDuty (alerting)
```

Key components:
1. **OTel SDK** in all services (auto-instrumentation for Python/FastAPI)
2. **OTel Collector** as DaemonSet + Deployment (batch, tail-sampling)
3. **Prometheus** for metrics (30d retention, downsampling)
4. **Tempo** for traces (object storage backend, 7d retention)
4. **Loki** for logs (structured, 30d retention)
5. **Grafana** for dashboards and alerting UI
6. **Alertmanager** for routing, inhibition, silencing

## Consequences

**Positive**:
- Vendor-neutral (OTel standard)
- Unified correlation (trace_id spans metrics/logs/traces)
- Cost-effective at scale (object storage for traces/logs)
- Rich ecosystem (auto-instrumentation, exporters)
- SLO-based alerting with burn-rate alerts

**Negative**:
- Multiple components to operate
- Trace sampling complexity (tail-based for errors)
- Cardinality management for metrics
- Learning curve for OTel concepts

## Alternatives Considered

1. **Datadog/New Relic**: Expensive at scale, vendor lock-in
2. **Elastic Stack**: Good but licensing, resource heavy
3. **Cloud provider (CloudWatch/X-Ray)**: Lock-in, limited customization
4. **Jaeger + Prometheus + EFK**: More components, no unified correlation

## Implementation Notes

- `capstone/infrastructure/observability/` - Helm values for kube-prometheus-stack, Tempo, Loki
- `capstone/serving/instrumentation.py` - OTel setup, custom metrics, span processors
- `capstone/infrastructure/observability/dashboards/` - Grafana dashboards as JSON
- `capstone/infrastructure/observability/alerts/` - PrometheusRule CRDs
- SLOs: Defined in `capstone/docs/slos.yaml` (latency, availability, quality)
- Sampling: 100% errors, 10% success, tail-based for latency outliers
- Exemplars: Link metrics to traces for p99 investigation