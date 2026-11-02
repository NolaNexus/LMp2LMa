"""Lightweight in-process metrics, drift detection, and alerting thresholds."""

from dataclasses import dataclass, field
from typing import Dict, List

import numpy as np


@dataclass
class RequestMetric:
    route: str
    latency_ms: float
    tokens: int
    provider: str
    success: bool = True


class MetricsCollector:
    """Bounded, thread-unsafe collector suitable for single-process demos."""

    def __init__(self, max_samples: int = 1000):
        self.max_samples = max_samples
        self._samples: List[RequestMetric] = []

    def record(self, metric: RequestMetric) -> None:
        self._samples.append(metric)
        if len(self._samples) > self.max_samples:
            self._samples = self._samples[-self.max_samples :]

    def summary(self) -> Dict[str, float]:
        if not self._samples:
            return {"requests": 0}
        latencies = np.array([m.latency_ms for m in self._samples])
        tokens = np.array([m.tokens for m in self._samples])
        successes = np.array([1.0 if m.success else 0.0 for m in self._samples])
        return {
            "requests": len(self._samples),
            "latency_p50_ms": round(float(np.percentile(latencies, 50)), 2),
            "latency_p95_ms": round(float(np.percentile(latencies, 95)), 2),
            "latency_p99_ms": round(float(np.percentile(latencies, 99)), 2),
            "tokens_per_request": round(float(tokens.mean()), 2),
            "error_rate": round(float(1 - successes.mean()), 4),
        }

    def alerts(self, latency_p95_ms: float = 2000.0, error_rate: float = 0.05) -> List[str]:
        summary = self.summary()
        fired = []
        if summary.get("latency_p95_ms", 0) > latency_p95_ms:
            fired.append(f"latency p95 {summary['latency_p95_ms']}ms exceeds {latency_p95_ms}ms")
        if summary.get("error_rate", 0) > error_rate:
            fired.append(f"error rate {summary['error_rate']} exceeds {error_rate}")
        return fired


@dataclass
class DriftDetector:
    """Cosine-centroid drift detector for query embeddings."""

    threshold: float = 0.25
    reference_centroid: np.ndarray | None = None
    _recent: List[np.ndarray] = field(default_factory=list)

    def set_reference(self, embeddings: List[List[float]]) -> None:
        self.reference_centroid = self._centroid(embeddings)

    def observe(self, embeddings: List[List[float]]) -> float | None:
        """Record embeddings and return drift score (0 = identical, 1 = orthogonal)."""
        self._recent.extend(np.asarray(embeddings, dtype=float))
        if self.reference_centroid is None or not len(self._recent):
            return None
        recent = self._centroid([e.tolist() for e in self._recent])
        return float(1 - np.dot(self.reference_centroid, recent))

    def is_drifting(self) -> bool:
        score = self.observe([]) if self._recent else None
        return bool(score is not None and score > self.threshold)

    @staticmethod
    def _centroid(embeddings: List[List[float]]) -> np.ndarray:
        matrix = np.asarray(embeddings, dtype=float)
        centroid = matrix.mean(axis=0)
        norm = np.linalg.norm(centroid)
        return centroid / norm if norm else centroid
