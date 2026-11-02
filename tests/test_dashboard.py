"""Smoke test for the Streamlit progress dashboard using streamlit.testing."""
from pathlib import Path

import pytest

streamlit = pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

APP = Path(__file__).resolve().parents[1] / "dashboard" / "app.py"


@pytest.mark.slow
def test_dashboard_renders_overview():
    at = AppTest.from_file(str(APP), default_timeout=30).run()
    assert not at.exception, f"dashboard raised: {at.exception}"
    assert any("Journey" in (h.value or "") for h in at.header)


@pytest.mark.slow
def test_dashboard_navigates_all_views():
    at = AppTest.from_file(str(APP), default_timeout=30).run()
    assert not at.exception

    radio = at.sidebar.radio[0]
    for view in ["Track Detail", "Checkpoints", "Final Exams"]:
        radio.set_value(view).run()
        assert not at.exception, f"view {view} raised: {at.exception}"