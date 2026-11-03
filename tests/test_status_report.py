"""The generated STATUS.md must satisfy its own consumers.

`tests/test_status_truth.py` parses track rows with a regex; the generator must
emit a row that regex matches, or the truth gate goes blind while still
reporting green.
"""

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import status_report  # noqa: E402

# Copied verbatim from tests/test_status_truth.py — the contract under test.
_ROW_RE = re.compile(r"^\|\s*(track-\d+-[\w-]+)\s*\|\s*(\d+)\s*\|", re.MULTILINE)


@pytest.fixture
def tree(tmp_path, monkeypatch):
    for name, count in {"track-01-a": 2, "track-02-b": 1}.items():
        d = tmp_path / name
        d.mkdir()
        for i in range(count):
            (d / f"0{i}.ipynb").write_text(json.dumps({"cells": []}))
    report = tmp_path / "report.md"
    report.write_text(
        "# Notebook Execution Report\n\n"
        "- Generated: 2026-11-02T00:00:00\n"
        "- QUICK_MODE: True\n\n"
        "| Notebook | Status | First error |\n|---|---|---|\n"
        "| `track-01-a/00.ipynb` | PASS |  |\n"
        "| `track-01-a/01.ipynb` | FAIL | ModuleNotFoundError: No module named 'x' |\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(status_report, "ROOT", tmp_path)
    monkeypatch.setattr(status_report, "REPORT", report)
    return tmp_path


def _render(tree):
    results, meta = status_report.read_report(status_report.REPORT)
    return status_report.render(results, meta, status_report.track_dirs())


def test_track_rows_match_the_truth_test_regex(tree):
    declared = dict(_ROW_RE.findall(_render(tree)))
    assert declared == {"track-01-a": "2", "track-02-b": "1"}


def test_unmeasured_track_is_not_given_a_number(tree):
    text = _render(tree)
    row = next(line for line in text.splitlines() if line.startswith("| track-02-b |"))
    assert "not measured" in row


def test_failures_carry_their_root_cause(tree):
    text = _render(tree)
    assert "ModuleNotFoundError: No module named 'x'" in text
    assert "| `track-01-a/01.ipynb` | FAIL |" in text


def test_stored_outputs_are_counted(tmp_path):
    track = tmp_path / "track-01-a"
    track.mkdir()
    (track / "empty.ipynb").write_text(
        json.dumps({"cells": [{"cell_type": "code", "outputs": []}]})
    )
    (track / "has.ipynb").write_text(
        json.dumps({"cells": [{"cell_type": "code", "outputs": [{"text": "x"}]}]})
    )
    assert status_report.count_stored_outputs(track) == 1
