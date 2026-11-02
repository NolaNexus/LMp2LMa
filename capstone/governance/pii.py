"""Deterministic PII redaction for inbound support text.

Applied before text is logged or forwarded to an LLM provider. Patterns favour
precision over recall: false positives degrade support quality, so only
well-formed identifiers are masked.
"""
import re
from dataclasses import dataclass, field
from typing import Dict, List, Pattern, Tuple

MASK = "[REDACTED:{kind}]"

PATTERNS: Tuple[Tuple[str, Pattern[str]], ...] = (
    ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("card", re.compile(r"\b(?:\d[ -]?){13,19}\b")),
    ("ssn", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("phone", re.compile(r"(?<!\d)(?:\+?\d{1,3}[ -]?)?(?:\(\d{3}\)|\d{3})[ -]\d{3}[ -]\d{4}(?!\d)")),
    ("ipv4", re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b")),
)

_ORDER = {"card": 0, "ssn": 1, "email": 2, "phone": 3, "ipv4": 4}


@dataclass
class Redaction:
    text: str
    counts: Dict[str, int] = field(default_factory=dict)

    @property
    def redacted(self) -> bool:
        return any(self.counts.values())


def _luhn(number: str) -> bool:
    digits = [int(d) for d in number if d.isdigit()]
    if len(digits) < 13:
        return False
    checksum = 0
    for position, digit in enumerate(reversed(digits)):
        if position % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
    return checksum % 10 == 0


def redact(text: str) -> Redaction:
    """Return redacted text and per-kind match counts."""
    counts: Dict[str, int] = {}
    spans: List[Tuple[int, int, str]] = []

    for kind, pattern in PATTERNS:
        for match in pattern.finditer(text):
            value = match.group(0)
            if kind == "card" and not _luhn(value):
                continue
            if any(start < match.end() and match.start() < end for start, end, _ in spans):
                continue
            spans.append((match.start(), match.end(), kind))
            counts[kind] = counts.get(kind, 0) + 1

    if not spans:
        return Redaction(text=text, counts={})

    spans.sort(key=lambda item: (item[0], _ORDER[item[2]]))
    pieces = []
    cursor = 0
    for start, end, kind in spans:
        pieces.append(text[cursor:start])
        pieces.append(MASK.format(kind=kind))
        cursor = end
    pieces.append(text[cursor:])
    return Redaction(text="".join(pieces), counts=counts)


def redact_text(text: str) -> str:
    """Convenience wrapper returning only the redacted string."""
    return redact(text).text
