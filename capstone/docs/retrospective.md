# Retrospective — LLM Customer Support Capstone

## What Worked

- **Provider abstraction first.** Defining `LLMProvider` and a registry before any
  business logic meant the mock provider could power tests and demos from day one,
  and swapping providers never touched the API layer.
- **Retrieval before generation.** Building citations into the response contract
  (`ChatResponse.citations`) forced grounded answers and made offline demos useful.
- **Deterministic CI.** TF-IDF retrieval plus a mock provider keeps the full test
  suite at ~2 seconds with no network or API keys.
- **Infrastructure as code from the start.** Helm lint plus `terraform validate`
  catches template errors before a cluster exists.

## What Did Not Work / Was Hard

- **Notebook corruption detour.** Earlier automated notebook rewrites double-escaped
  quotes and truncated cells; most of the schedule went to recovering source from
  git history and adding a structural validator (`tools/validate_notebooks.py`).
- **Library drift.** MLflow 3.x rejected the filesystem backend and switched sklearn
  serialization to skops, breaking notebooks written for 2.x. Pinning `mlflow<3`
  and adding `MLFLOW_ALLOW_FILE_STORE` restored behaviour.
- **Heavy notebook execution.** Full CIFAR-10/TensorFlow runs are unsuitable for CI;
  `QUICK_MODE` subsets were required to make execution gates realistic.
- **Grading is heuristic.** Checkpoints do not map questions to cells, so the grader
  scores "any output contains the expectation". Precise grading needs a cell mapping.

## Metrics

| Area | Before | After |
|---|---|---|
| Notebooks valid (JSON + AST) | 17/32 | 32/32 |
| Grader status | crashes on non-string expectations | PASS/FAIL/NOT_EXECUTED |
| CI pipeline | installed from PyTorch index, no notebook execution | validates, executes fast subset, grades |
| Capstone tests | 0 | 14 |
| Service endpoints | none | `/health`, `/chat`, `/tickets/classify` |

## Future Improvements

1. **Embedding retrieval** behind `FaqRetriever`, with a vector store and evaluation set.
2. **Cell-level checkpoint mapping** to make the grader exact.
3. **Prometheus exporter** for metrics instead of in-process collection.
4. **PII redaction** in the request path before logging or provider calls.
5. **Load testing** (k6/Locust) to validate the 2-replica + HPA assumption.
6. **Prompt A/B testing** using the provider registry and run metadata.
7. **Cost dashboard** driven by `tokens_per_request` metrics.

## Lessons on Architecture

- Isolate the volatile dependency (the LLM vendor) behind a port; everything else
  can stay simple.
- Make the offline path the default path for tests; network is an exception, not a
  prerequisite.
- Health checks, resource limits, and a rollback command are the minimum production
  surface — write them before the first deploy.
