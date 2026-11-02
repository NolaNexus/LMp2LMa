"""Generate the Track 4 architecture notebooks (07–12).

Each notebook uses only the standard library plus numpy/pandas/torch where
already required by the track, and stays fast in QUICK_MODE.
"""
import json
from pathlib import Path

import nbformat

ROOT = Path(__file__).resolve().parent.parent

META = {
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python"},
}


def md(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": text.strip() + "\n"}


def code(text: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": text.strip() + "\n",
    }


NOTEBOOKS = {}

# ---------------------------------------------------------------- 07 system design
NOTEBOOKS["07_system_design.ipynb"] = [
    md(
        """
# 07 — System Design for ML Platforms

**Objectives**
- Translate product requirements (QPS, latency SLO) into capacity plans.
- Apply Little's law and a queueing approximation to size replicas.
- Build a cost model and expose the tradeoff between headroom and spend.

Exercise: fill in the `requirements` block for your own scenario and re-run.
"""
    ),
    code(
        """
import math

requirements = {
    "qps_peak": 120,              # requests per second at peak
    "latency_slo_ms": 300,        # p99 target
    "avg_latency_ms": 120,        # measured single-request latency
    "gpu_throughput_rps": 25,     # requests/sec one replica sustains
    "headroom": 1.4,              # safety factor for bursts/failures
    "gpu_hourly_usd": 3.06,
}

replicas = math.ceil(requirements["qps_peak"] * requirements["headroom"] / requirements["gpu_throughput_rps"])
print(f"replicas_needed: {replicas}")
print(f"provisioned throughput: {replicas * requirements['gpu_throughput_rps']:.0f} req/s")
"""
    ),
    code(
        """
# Little's law: concurrency L = arrival rate (lambda) * time in system (W)
lam = requirements["qps_peak"]
W = requirements["avg_latency_ms"] / 1000
concurrency = lam * W
print(f"concurrent_requests: {concurrency:.1f}")

# M/M/c queue approximation for the probability of queueing
def erlang_c(c: int, offered_load: float) -> float:
    a = offered_load
    top = (a ** c) / math.factorial(c) * c / (c - a) if a < c else float("inf")
    bottom = sum((a ** k) / math.factorial(k) for k in range(c)) + top
    return top / bottom if bottom else 1.0

per_replica_load = lam / requirements["gpu_throughput_rps"]
p_queue = erlang_c(replicas, per_replica_load)
print(f"utilization_per_replica: {per_replica_load:.2f}")
print(f"probability_of_queueing: {p_queue:.3f}")
"""
    ),
    code(
        """
# Cost model: idle headroom is insurance, not waste (until it is)
hours_per_month = 730
monthly_cost = replicas * requirements["gpu_hourly_usd"] * hours_per_month
requests_per_month = requirements["qps_peak"] * 60 * 60 * hours_per_month
cost_per_1k = monthly_cost / (requests_per_month / 1000)

print(f"monthly_gpu_cost_usd: {monthly_cost:,.0f}")
print(f"cost_per_1k_requests_usd: {cost_per_1k:.4f}")
print("SLO review: p99 target", requirements["latency_slo_ms"], "ms")
"""
    ),
    md(
        """
**Architect's checklist**
1. Capacity must be sized for *peak*, not average; keep an explicit headroom factor.
2. Queueing probability explodes as utilization approaches 1 — the last 10% of
   utilization buys very little throughput and a lot of tail latency.
3. Cost per 1K requests is the metric to compare against business value.
"""
    ),
]

# ---------------------------------------------------------------- 08 data architecture
NOTEBOOKS["08_data_architecture.ipynb"] = [
    md(
        """
# 08 — Data Architecture (Medallion Layers)

**Objectives**
- Model bronze → silver → gold layers with explicit contracts.
- Make ingestion idempotent (dedupe by event key).
- Validate schema changes before they reach downstream consumers.
"""
    ),
    code(
        """
import pandas as pd

bronze = pd.DataFrame({
    "event_id": ["e1", "e2", "e2", "e3", "e4"],
    "user_id": ["u1", "u1", "u1", "u2", "u2"],
    "event": ["view", "click", "click", "purchase", "view"],
    "amount": [0.0, 0.0, 0.0, 42.5, 0.0],
    "ingested_at": pd.date_range("2026-01-01", periods=5, freq="min"),
})
print("bronze_rows:", len(bronze))
print(bronze.head())
"""
    ),
    code(
        """
# Silver: enforce the data contract, then deduplicate on event_id
REQUIRED_COLUMNS = {"event_id", "user_id", "event", "amount"}

def validate(df: pd.DataFrame) -> list[str]:
    problems = []
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        problems.append(f"missing columns: {sorted(missing)}")
    if (df["amount"] < 0).any():
        problems.append("negative amounts")
    if df["event_id"].isna().any():
        problems.append("null event ids")
    return problems

problems = validate(bronze)
print("contract_violations:", problems)

silver = bronze.drop_duplicates(subset="event_id", keep="last").copy()
print("silver_rows:", len(silver))
"""
    ),
    code(
        """
# Gold: business aggregates with a stable grain
gold = (silver.groupby("user_id", as_index=False)
              .agg(events=("event_id", "count"), revenue=("amount", "sum")))
print(gold)
print("gold_grain: one row per user")
"""
    ),
    code(
        """
# Schema evolution check: additive changes are safe, removals are breaking
old_schema = {"event_id", "user_id", "event", "amount"}
new_schema = {"event_id", "user_id", "event", "amount", "device"}

print("breaking_change:", bool(old_schema - new_schema))
print("additive_fields:", sorted(new_schema - old_schema))
"""
    ),
    md(
        """
**Design notes**
- Bronze is append-only raw truth; never mutate it.
- Silver owns contracts and dedupe; replaying bronze must reproduce silver exactly.
- Gold is disposable: rebuild from silver whenever definitions change.
"""
    ),
]

# ---------------------------------------------------------------- 09 platform engineering
NOTEBOOKS["09_platform_engineering.ipynb"] = [
    md(
        """
# 09 — Platform Engineering: Batch, Stream, and Promotion Gates

**Objectives**
- Compare Lambda (batch + speed) with Kappa (stream-only) pipelines.
- Encode model promotion as executable policy, not tribal knowledge.
- Simulate a CI gate that blocks unqualified models.
"""
    ),
    code(
        """
from collections import defaultdict

events = [
    {"minute": 0, "value": 5}, {"minute": 0, "value": 3},
    {"minute": 1, "value": 8}, {"minute": 2, "value": 2},
]

# Stream view: incremental fold, visible immediately
stream = defaultdict(int)
for e in events:
    stream[e["minute"]] += e["value"]
print("stream_aggregates:", dict(sorted(stream.items())))

# Batch view: reprocess everything at the end of the window
batch = defaultdict(int)
for e in events:
    batch[e["minute"]] += e["value"]
print("batch_matches_stream:", dict(batch) == dict(stream))
"""
    ),
    code(
        """
# Model promotion policy
def promotion_gate(metrics: dict) -> dict:
    rules = {
        "accuracy >= 0.90": metrics["accuracy"] >= 0.90,
        "auc >= 0.85": metrics["auc"] >= 0.85,
        "latency_p95_ms <= 150": metrics["latency_p95_ms"] <= 150,
        "no_regression_vs_champion": metrics["accuracy"] >= metrics["champion_accuracy"],
    }
    return {"pass": all(rules.values()), "rules": rules}

candidates = {
    "model_a": {"accuracy": 0.92, "auc": 0.88, "latency_p95_ms": 120, "champion_accuracy": 0.91},
    "model_b": {"accuracy": 0.94, "auc": 0.90, "latency_p95_ms": 240, "champion_accuracy": 0.91},
}
decisions = {name: promotion_gate(m) for name, m in candidates.items()}
for name, decision in decisions.items():
    print(name, "promote" if decision["pass"] else "block", decision["rules"])
print("promoted_count:", sum(1 for d in decisions.values() if d["pass"]))
"""
    ),
    code(
        """
# CI gate: all stages must pass before an artifact is deployable
stages = {"unit": True, "integration": True, "performance": False, "security": True}
failed = [name for name, ok in stages.items() if not ok]
print("deploy_allowed:", not failed)
print("failed_stages:", failed)
"""
    ),
    md(
        """
**Decision guide**
- Kappa when replaying the log is cheap and one codebase is worth more than
  separate batch correctness.
- Promotion policy belongs in version control next to the model config so the
  same rules apply in CI and production.
"""
    ),
]

# ---------------------------------------------------------------- 10 serving architecture
NOTEBOOKS["10_serving_architecture.ipynb"] = [
    md(
        """
# 10 — Serving Architecture: Batching, Caching, Canary

**Objectives**
- Quantify the latency/throughput tradeoff of dynamic batching.
- Size a cache from the hit-rate curve.
- Use an error budget to decide canary promotion vs rollback.
"""
    ),
    code(
        """
import numpy as np

def simulate_batch(batch_size: int, base_ms: float = 20, per_item_ms: float = 2.0, qps: float = 500):
    # Larger batches amortize per-request overhead but add queueing delay
    compute_ms = base_ms + per_item_ms * batch_size
    queue_wait_ms = (batch_size / qps) * 1000 / 2
    throughput = batch_size / (compute_ms / 1000)
    return {"batch_size": batch_size, "latency_ms": compute_ms + queue_wait_ms,
            "throughput_rps": throughput}

results = [simulate_batch(b) for b in (1, 4, 8, 16, 32, 64)]
for r in results:
    print(f"batch={r['batch_size']:>2} latency={r['latency_ms']:7.1f}ms throughput={r['throughput_rps']:8.1f} rps")

best = max((r for r in results if r["latency_ms"] <= 300), key=lambda r: r["throughput_rps"])
print("optimal_batch_size:", best["batch_size"])
"""
    ),
    code(
        """
# Cache sizing: effective backend load falls with hit rate
qps = 500
for hit_rate in (0.0, 0.5, 0.8, 0.9, 0.95):
    backend_qps = qps * (1 - hit_rate)
    print(f"hit_rate={hit_rate:.2f} backend_qps={backend_qps:6.1f}")

hit_rate = 0.9
print("backend_qps_at_90pct:", qps * (1 - hit_rate))
"""
    ),
    code(
        """
# Canary decision from an error budget
error_budget = 0.001          # 0.1% of requests may fail
canary_requests = 50_000
canary_errors = 80

observed_error_rate = canary_errors / canary_requests
budget_consumed = observed_error_rate / error_budget
print(f"observed_error_rate: {observed_error_rate:.5f}")
print(f"error_budget_consumed: {budget_consumed:.2f}x")
print("decision:", "promote" if budget_consumed <= 1.0 else "rollback")
"""
    ),
    md(
        """
**Architect's notes**
- Dynamic batching maximizes GPU utilization but every millisecond of queue wait is
  paid by the user; pick the knee of the curve, not the maximum batch.
- A cache is a latency lever and a consistency risk: define invalidation first.
- Canaries are cheap insurance; automate the promote/rollback decision with budgets.
"""
    ),
]

# ---------------------------------------------------------------- 11 IaC
NOTEBOOKS["11_iac.ipynb"] = [
    md(
        """
# 11 — Infrastructure as Code for ML Platforms

**Objectives**
- Generate Terraform and Kubernetes manifests programmatically.
- Enforce policy-as-code checks before anything reaches a cluster.
- Treat infrastructure changes with the same review rigor as application code.
"""
    ),
    code(
        """
config = {
    "service": "customer-support",
    "image": "ghcr.io/example/customer-support:1.0.0",
    "replicas": 2,
    "cpu": "500m",
    "memory": "1Gi",
    "port": 8000,
}
print(config)
"""
    ),
    code(
        """
tf = f'''
resource "kubernetes_namespace" "{config['service'].replace('-', '_')}" {{
  metadata {{
    name = "{config['service']}"
  }}
}}

resource "helm_release" "{config['service'].replace('-', '_')}" {{
  name      = "{config['service']}"
  chart     = "./helm/{config['service']}"
  namespace = kubernetes_namespace.{config['service'].replace('-', '_')}.metadata[0].name
}}
'''
Path = __import__("pathlib").Path
Path("/tmp/iac_demo").mkdir(exist_ok=True)
Path("/tmp/iac_demo/main.tf").write_text(tf)
print("terraform_generated: /tmp/iac_demo/main.tf")
print(tf)
"""
    ),
    code(
        """
import yaml

manifest = {
    "apiVersion": "apps/v1",
    "kind": "Deployment",
    "metadata": {"name": config["service"]},
    "spec": {
        "replicas": config["replicas"],
        "selector": {"matchLabels": {"app": config["service"]}},
        "template": {
            "metadata": {"labels": {"app": config["service"]}},
            "spec": {
                "containers": [{
                    "name": "api",
                    "image": config["image"],
                    "ports": [{"containerPort": config["port"]}],
                    "resources": {
                        "requests": {"cpu": config["cpu"], "memory": config["memory"]},
                        "limits": {"cpu": config["cpu"], "memory": config["memory"]},
                    },
                    "securityContext": {"runAsNonRoot": True, "allowPrivilegeEscalation": False},
                }]
            },
        },
    },
}
Path("/tmp/iac_demo/deployment.yaml").write_text(yaml.safe_dump(manifest))
print(yaml.safe_dump(manifest))
"""
    ),
    code(
        """
# Policy-as-code: catch the classic production foot-guns before apply
def check_policies(manifest: dict) -> list[str]:
    container = manifest["spec"]["template"]["spec"]["containers"][0]
    violations = []
    if container["image"].endswith(":latest"):
        violations.append("image tag must be immutable (not :latest)")
    if "limits" not in container.get("resources", {}):
        violations.append("resource limits required")
    if not container.get("securityContext", {}).get("runAsNonRoot"):
        violations.append("runAsNonRoot required")
    return violations

violations = check_policies(manifest)
print("policy_violations:", violations)
"""
    ),
    md(
        """
**Review checklist**
1. Images pinned by digest or immutable tag.
2. Resource requests *and* limits set — requests schedule, limits protect neighbors.
3. Security context explicit; no privilege escalation.
4. Changes go through plan → review → apply, never `apply -auto-approve` in prod.
"""
    ),
]

# ---------------------------------------------------------------- 12 profiling
NOTEBOOKS["12_profiling.ipynb"] = [
    md(
        """
# 12 — Profiling and Performance Engineering

**Objectives**
- Measure before optimizing: wall-clock, throughput, and memory.
- Use `torch.profiler` to find the real hotspot.
- Estimate parameters/FLOPs to reason about capacity before benchmarks.
"""
    ),
    code(
        """
import os
import time
import torch
import torch.nn as nn

torch.manual_seed(0)
QUICK_MODE = os.getenv("QUICK_MODE", "0") == "1"

model = nn.Sequential(
    nn.Linear(512, 1024), nn.ReLU(),
    nn.Linear(1024, 1024), nn.ReLU(),
    nn.Linear(1024, 10),
)
x = torch.randn(64, 512)

steps = 5 if QUICK_MODE else 50
start = time.perf_counter()
for _ in range(steps):
    loss = model(x).sum()
    loss.backward()
    model.zero_grad()
elapsed = time.perf_counter() - start
print(f"steps: {steps}")
print(f"per_step_ms: {elapsed / steps * 1000:.2f}")
print(f"throughput_samples_per_s: {steps * x.shape[0] / elapsed:.0f}")
"""
    ),
    code(
        """
# Where does the time actually go?
from torch.profiler import ProfilerActivity, profile

with profile(activities=[ProfilerActivity.CPU], record_shapes=True) as prof:
    for _ in range(3):
        model(x).sum().backward()
        model.zero_grad()

print(prof.key_averages().table(sort_by="cpu_time_total", row_limit=8))
"""
    ),
    code(
        """
params = sum(p.numel() for p in model.parameters())
flops_per_sample = 2 * sum(
    layer.in_features * layer.out_features
    for layer in model
    if isinstance(layer, nn.Linear)
)
print(f"parameters: {params:,}")
print(f"flops_per_sample: {flops_per_sample:,}")
print(f"memory_params_mb: {params * 4 / 1024**2:.2f}")
"""
    ),
    md(
        """
**Method**
1. Baseline: wall-clock + throughput at a realistic batch size.
2. Profile: sort by CPU/CUDA time; ignore noise below a few percent.
3. Optimize the top item, then re-measure. Keep a record of before/after.

Never tune on a single run — warm-up and variance will fool you.
"""
    ),
]


EXECUTION_COUNTS = None


def build(name: str, cells: list[dict]) -> dict:
    nb = {
        "cells": [],
        "metadata": META,
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    for cell in cells:
        cell = dict(cell)
        if cell["cell_type"] == "code":
            cell.setdefault("execution_count", None)
            cell.setdefault("outputs", [])
        cell.setdefault("id", f"{name[:6]}-{len(nb['cells'])}")
        nb["cells"].append(cell)
    nbformat.validate(nbformat.from_dict(nb))
    return nb


def main() -> int:
    for name, cells in NOTEBOOKS.items():
        path = ROOT / "track-04-ml-architect" / name
        nb = build(name, cells)
        path.write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n")
        print(f"WROTE {path.relative_to(ROOT)} ({len(nb['cells'])} cells)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())