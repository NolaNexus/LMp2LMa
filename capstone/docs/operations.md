# Operations Guide — LLM Customer Support

## Service Level Objectives

| SLO | Target | Measurement |
|---|---|---|
| Availability | 99.9% monthly | `/health` probes, incident log |
| Latency p95 | < 2 000 ms | `MetricsCollector.summary()` |
| Error rate | < 5% | `MetricsCollector.alerts()` |
| Grounded answers | 100% with citations | `/chat` responses include `citations` |

## Local Run

```bash
conda activate ml-arch
uvicorn capstone.serving.api.app:app --host 0.0.0.0 --port 8000
curl -s localhost:8000/health
curl -s -X POST localhost:8000/chat -H 'content-type: application/json' \
  -d '{"message": "How do I reset my password?"}'
```

Tests:

```bash
python -m pytest capstone/tests -q
python -m pytest capstone/tests -q -m "not slow"
```

## Deploy

1. Build and push the image:
   ```bash
   docker build -f capstone/infrastructure/Dockerfile -t ghcr.io/example/customer-support:1.0.0 .
   docker push ghcr.io/example/customer-support:1.0.0
   ```
2. Render the chart (sanity check):
   ```bash
   helm lint capstone/infrastructure/helm/customer-support
   helm template customer-support capstone/infrastructure/helm/customer-support
   ```
3. Apply with Terraform:
   ```bash
   cd capstone/infrastructure/terraform
   terraform init
   terraform validate
   terraform apply -var image_tag=1.0.0
   ```

## Rollback

- Helm: `helm rollback customer-support <REVISION> -n customer-support`
- Terraform: revert the `image_tag` variable and `terraform apply`.
- Verify: `kubectl -n customer-support rollout status deploy/customer-support`
  then `GET /health` must report `{"status": "ok"}`.

## Scaling

- HPA targets 70% CPU, 2–10 replicas (`values.yaml`).
- Vertical concerns: raise `resources.limits.memory` before raising replica count if
  the corpus grows large.
- Retrieval is in-process and CPU-bound; replicas scale horizontally.

## Incident Runbook

**Elevated p95 latency**
1. Check `MetricsCollector.alerts()` output or dashboards.
2. Distinguish retrieval time vs provider time (latency recorded per request).
3. If provider-bound: switch `LLM_PROVIDER=mock` to shed load, or raise fallback.
4. If retrieval-bound: reduce `top_k`, or scale replicas.

**Provider outage**
1. `/health` reports `provider_healthy: false`.
2. Registry `generate_with_fallback` moves to the next provider in the chain.
3. If all providers fail, `/chat` returns HTTP 500; switch to `mock` for degraded
   but functional service and page the provider owner.

**Drift alert**
1. `DriftDetector.is_drifting()` true means query distribution shifted.
2. Export recent queries (provider metadata) and compare to the FAQ corpus topics.
3. Update `capstone/data/raw/faqs.json` or retrain the retriever; re-run
   `pytest capstone/tests`.

**Wrong or unsafe answer**
1. Capture the request, the returned `citations`, and provider/model ids.
2. Add the case to tests (`capstone/tests/test_api.py`) as a regression.
3. If policy violation, disable the provider via `LLM_PROVIDER=mock` and escalate.

## Security Checklist

- Provider keys only via environment variables; never in image layers.
- Container runs as non-root (uid 10001).
- Request bodies validated and length-limited by pydantic models.
- No customer PII persisted by the demo service; add PII redaction before storing.

## Cost Controls

- `max_tokens` bounded per request.
- Mock provider in CI keeps pipeline cost at zero.
- Track `tokens_per_request` in metrics; alert when the 7-day mean rises >20%.
