"""STATUS.md must agree with the filesystem.

STATUS.md is the top of the source-of-truth hierarchy (docs/ROADMAP.md §0).
If it drifts from reality, every downstream decision is wrong.
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
STATUS = ROOT / "STATUS.md"

TRACKS = [
    "track-01-ml-programmer",
    "track-02-dl-programmer",
    "track-03-ml-engineer",
    "track-04-ml-architect",
]

# Matches a STATUS.md table row: | track-01-ml-programmer | 7 | 7/7 | 1/7 | 0/7 |
_ROW_RE = re.compile(r"^\|\s*(track-\d+-[\w-]+)\s*\|\s*(\d+)\s*\|", re.MULTILINE)

_SKIP = pytest.mark.skipif(not STATUS.exists(), reason="STATUS.md not generated yet (Tier 0.2)")


def _declared() -> dict[str, int]:
    text = STATUS.read_text(encoding="utf-8")
    return {m.group(1): int(m.group(2)) for m in _ROW_RE.finditer(text)}


def _actual() -> dict[str, int]:
    return {t: len(list((ROOT / t).glob("*.ipynb"))) for t in TRACKS}


@_SKIP
def test_status_declares_every_track():
    declared = _declared()
    missing = [t for t in TRACKS if t not in declared]
    assert not missing, f"STATUS.md omits: {', '.join(missing)}"


@_SKIP
def test_status_counts_match_filesystem():
    declared, actual = _declared(), _actual()
    mismatches = [
        f"{t}: STATUS says {declared.get(t, 'missing')}, disk has {actual[t]}"
        for t in TRACKS
        if declared.get(t) != actual[t]
    ]
    assert not mismatches, "; ".join(mismatches)
