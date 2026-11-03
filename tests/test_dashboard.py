"""Smoke test for the Streamlit progress dashboard using streamlit.testing."""

import importlib.util
from pathlib import Path

import pytest

streamlit = pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

APP = Path(__file__).resolve().parents[1] / "dashboard" / "app.py"


def _load_app():
    spec = importlib.util.spec_from_file_location("dash_app", APP)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_tracks_are_derived_from_the_filesystem(tmp_path, monkeypatch):
    """A1: a fifth track directory must not IndexError the overview."""
    app = _load_app()
    for i in range(1, 6):
        (tmp_path / f"track-0{i}-placeholder").mkdir()
    monkeypatch.setattr(app, "NOTEBOOK_DIR", tmp_path)
    tracks = app.discover_tracks()
    assert len(tracks) == 5
    assert all(tracks.values()), "every track needs a display name"


def test_unknown_track_title_is_derived():
    app = _load_app()
    assert app.track_title("track-05-red-teaming") == "Track 05 Red Teaming"


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
