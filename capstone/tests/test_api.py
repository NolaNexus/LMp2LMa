"""Contract tests for the customer-support FastAPI service (mock provider)."""
import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from capstone.serving.api.app import app  # noqa: E402

client = TestClient(app)


def test_health_reports_provider_and_corpus():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["provider"] == "mock"
    assert body["faq_documents"] >= 8


def test_chat_grounds_response_in_faq():
    response = client.post("/chat", json={"message": "How do I reset my password?"})
    assert response.status_code == 200
    body = response.json()
    assert body["citations"], "expected retrieved citations"
    assert "FAQ-001" in body["citations"]
    assert body["response"]
    assert body["latency_ms"] >= 0


def test_chat_validates_empty_message():
    response = client.post("/chat", json={"message": ""})
    assert response.status_code == 422


def test_classify_billing():
    response = client.post(
        "/tickets/classify",
        json={"subject": "Refund request", "body": "My payment failed and I want a refund for this invoice"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["category"] == "billing"
    assert body["confidence"] > 0.5


def test_classify_falls_back_to_general():
    response = client.post("/tickets/classify", json={"body": "Hello there"})
    assert response.status_code == 200
    assert response.json()["category"] == "general"