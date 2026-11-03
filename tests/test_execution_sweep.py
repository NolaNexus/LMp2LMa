"""Sweep error extraction and status classification.

A8: `first_error()` must return the root cause, not the traceback's `raise` line.
A11: `CellTimeoutError` is a resource classification (`NEEDS_GPU`), not `FAIL`.

Sample tracebacks below are verbatim `jupyter nbconvert --execute` output,
2026-11-02, nbclient emitted module-qualified exception names.
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import execution_sweep  # noqa: E402
from execution_sweep import classify, first_error  # noqa: E402

# Two raise sites, one root cause: the old implementation returned the first.
MISSING_DEP = """
Traceback (most recent call last):
  File "/x/nbconvert/preprocessors/execute.py", line 123, in preprocess_cell
    raise CellExecutionError.from_cell_and_msg(cell, out)
nbclient.exceptions.CellExecutionError: An error occurred while executing the following cell:
------------------
import sklearn
------------------

ModuleNotFoundError: No module named 'sklearn'
"""

TIMEOUT = """Traceback (most recent call last):
  File "/x/nbclient/client.py", line 856, in _async_handle_timeout
    raise CellTimeoutError.error_from_timeout_and_cell(
nbclient.exceptions.CellTimeoutError: A cell timed out while it was being executed, after 1 seconds.
The message was: Cell execution timed out.
"""


def test_missing_dependency_reports_root_cause():
    detail = first_error(MISSING_DEP)
    assert detail.startswith("ModuleNotFoundError")
    assert "sklearn" in detail


def test_exception_name_is_not_module_qualified():
    detail = first_error(TIMEOUT)
    assert detail.startswith("CellTimeoutError:")
    assert "nbclient." not in detail


def test_timeout_is_needs_gpu_not_fail():
    assert classify(False, first_error(TIMEOUT)) == "NEEDS_GPU"


def test_broken_notebook_is_fail():
    assert classify(False, first_error(MISSING_DEP)) == "FAIL"


def test_success_is_pass():
    assert classify(True, "") == "PASS"


def test_detail_is_bounded():
    assert len(first_error("RuntimeError: " + "x" * 1000)) <= 300


def test_empty_output_is_empty_string():
    assert first_error("") == ""


@pytest.mark.parametrize("ok, expected", [(True, 0), (False, 2)])
def test_env_check_is_a_gate_and_exits(monkeypatch, ok, expected):
    """`--env-check` must report and stop; a silent 38-notebook sweep is a bug."""
    monkeypatch.setattr(sys, "argv", ["execution_sweep.py", "--env-check"])
    monkeypatch.setattr(execution_sweep, "env_check", lambda: ok)

    def _swept(only):  # pragma: no cover - fails the test if called
        raise AssertionError("--env-check must not start a sweep")

    monkeypatch.setattr(execution_sweep, "notebooks", _swept)
    assert execution_sweep.main() == expected


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
