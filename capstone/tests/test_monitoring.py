"""Tests for metrics collection and drift detection."""
import numpy as np

from capstone.monitoring.metrics import DriftDetector, MetricsCollector, RequestMetric


def test_metrics_summary_percentiles():
    collector = MetricsCollector()
    for latency in (100, 120, 140, 900):
        collector.record(RequestMetric(route="/chat", latency_ms=latency, tokens=50, provider="mock"))
    summary = collector.summary()
    assert summary["requests"] == 4
    assert summary["latency_p50_ms"] == 130.0
    assert summary["latency_p95_ms"] >= 140


def test_metrics_alerts_fire_on_latency():
    collector = MetricsCollector()
    for _ in range(10):
        collector.record(RequestMetric(route="/chat", latency_ms=5000, tokens=10, provider="mock"))
    alerts = collector.alerts(latency_p95_ms=2000)
    assert alerts and "latency" in alerts[0]


def test_drift_detector_flags_shifted_queries():
    detector = DriftDetector(threshold=0.2)
    rng = np.random.default_rng(0)
    reference = rng.normal(size=(50, 8)).tolist()
    detector.set_reference(reference)
    shifted = (rng.normal(size=(50, 8)) + 3.0).tolist()
    score = detector.observe(shifted)
    assert score is not None
    assert detector.is_drifting()


def test_drift_detector_ignores_identical_distribution():
    detector = DriftDetector(threshold=0.2)
    rng = np.random.default_rng(1)
    reference = rng.normal(size=(50, 8)).tolist()
    detector.set_reference(reference)
    assert detector.observe(reference) is not None
    assert not detector.is_drifting()