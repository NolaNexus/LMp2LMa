"""Tests for deterministic PII redaction."""
import pytest

from capstone.governance.pii import redact, redact_text


def test_redacts_email_phone_and_card():
    text = (
        "Email jane.doe@example.com or call +1 (555) 123-4567. "
        "Card 4111 1111 1111 1111 was declined."
    )
    result = redact(text)
    assert result.redacted
    assert result.counts == {"email": 1, "phone": 1, "card": 1}
    assert "jane.doe@example.com" not in result.text
    assert "4111" not in result.text
    assert "[REDACTED:email]" in result.text
    assert "[REDACTED:card]" in result.text
    assert "[REDACTED:phone]" in result.text


def test_redacts_ssn_and_ipv4():
    result = redact("SSN 123-45-6789 from host 192.168.1.10")
    assert result.counts == {"ssn": 1, "ipv4": 1}
    assert result.text == "SSN [REDACTED:ssn] from host [REDACTED:ipv4]"


def test_ignores_non_luhn_digit_runs():
    text = "Order 1234567890123 shipped"
    result = redact(text)
    assert not result.redacted
    assert result.text == text


def test_clean_text_unchanged():
    text = "How do I reset my password?"
    assert redact_text(text) == text


def test_redaction_idempotent():
    once = redact_text("Contact a@b.io")
    twice = redact_text(once)
    assert once == twice
