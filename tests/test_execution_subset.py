"""Tests for the generated CI execution subset (A2)."""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from execution_subset import select  # noqa: E402


def _touch_notebooks(track: Path, names):
    track.mkdir(parents=True, exist_ok=True)
    for name in names:
        (track / name).write_text("{}")


def test_select_follows_checkpoint_order(tmp_path):
    track = tmp_path / "track-01-ml-programmer"
    _touch_notebooks(track, ["01_first.ipynb", "02_second.ipynb", "03_third.ipynb"])
    cp_dir = tmp_path / "checkpoints"
    cp_dir.mkdir()
    (cp_dir / "track_01_ml_programmer.json").write_text(
        json.dumps(
            {
                "track": "Track 1",
                "checkpoints": [{"notebook": "03_third.ipynb"}, {"notebook": "01_first.ipynb"}],
                "final_exam": {},
            }
        )
    )

    assert select(root=tmp_path, per_track=2, checkpoint_dir=cp_dir) == [
        "track-01-ml-programmer/03_third.ipynb",
        "track-01-ml-programmer/01_first.ipynb",
    ]


def test_select_skips_missing_notebooks_and_falls_back_to_filenames(tmp_path):
    track = tmp_path / "track-02-dl-programmer"
    _touch_notebooks(track, ["01_a.ipynb", "02_b.ipynb"])
    cp_dir = tmp_path / "checkpoints"
    cp_dir.mkdir()
    (cp_dir / "track_02_dl_programmer.json").write_text(
        json.dumps({"checkpoints": [{"notebook": "09_deleted.ipynb"}], "final_exam": {}})
    )

    assert select(root=tmp_path, per_track=2, checkpoint_dir=cp_dir) == [
        "track-02-dl-programmer/01_a.ipynb",
        "track-02-dl-programmer/02_b.ipynb",
    ]


def test_select_truncates_to_per_track(tmp_path):
    track = tmp_path / "track-03-ml-engineer"
    _touch_notebooks(track, ["01_a.ipynb", "02_b.ipynb", "03_c.ipynb"])
    cp_dir = tmp_path / "checkpoints"
    cp_dir.mkdir()

    assert select(root=tmp_path, per_track=1, checkpoint_dir=cp_dir) == [
        "track-03-ml-engineer/01_a.ipynb"
    ]


def test_select_can_restrict_tracks(tmp_path):
    _touch_notebooks(tmp_path / "track-01-ml-programmer", ["01_a.ipynb"])
    _touch_notebooks(tmp_path / "track-02-dl-programmer", ["01_b.ipynb"])
    cp_dir = tmp_path / "checkpoints"
    cp_dir.mkdir()

    assert select(
        root=tmp_path, per_track=1, tracks=["track-02-dl-programmer"], checkpoint_dir=cp_dir
    ) == ["track-02-dl-programmer/01_b.ipynb"]


def test_select_rejects_negative_budget(tmp_path):
    with pytest.raises(ValueError):
        select(root=tmp_path, per_track=-1)


def test_select_uses_measured_green_tracks_only(tmp_path):
    _touch_notebooks(tmp_path / "track-01-ml-programmer", ["01_a.ipynb", "02_b.ipynb"])
    _touch_notebooks(tmp_path / "track-02-dl-programmer", ["01_c.ipynb"])
    cp_dir = tmp_path / "checkpoints"
    cp_dir.mkdir()
    (tmp_path / "STATUS.md").write_text(
        "# STATUS\n\n"
        "| Track | Notebooks | Executed | Passed | Stored outputs |\n"
        "|---|---|---|---|---|\n"
        "| track-01-ml-programmer | 2 | 2 | 2 | 0 |\n"
        "| track-02-dl-programmer | 1 | not measured | — | 0 |\n"
    )

    assert select(root=tmp_path, per_track=2, checkpoint_dir=cp_dir) == [
        "track-01-ml-programmer/01_a.ipynb",
        "track-01-ml-programmer/02_b.ipynb",
    ]
    assert select(root=tmp_path, per_track=2, checkpoint_dir=cp_dir, measured_only=False) == [
        "track-01-ml-programmer/01_a.ipynb",
        "track-01-ml-programmer/02_b.ipynb",
        "track-02-dl-programmer/01_c.ipynb",
    ]


def test_select_ignores_a_track_with_failures(tmp_path):
    _touch_notebooks(tmp_path / "track-01-ml-programmer", ["01_a.ipynb"])
    _touch_notebooks(tmp_path / "track-02-dl-programmer", ["01_b.ipynb"])
    cp_dir = tmp_path / "checkpoints"
    cp_dir.mkdir()
    (tmp_path / "STATUS.md").write_text(
        "| Track | Notebooks | Executed | Passed | Stored outputs |\n"
        "|---|---|---|---|---|\n"
        "| track-01-ml-programmer | 1 | 1 | 1 | 0 |\n"
        "| track-02-dl-programmer | 2 | 2 | 1 | 0 |\n"
    )

    assert select(root=tmp_path, per_track=1, checkpoint_dir=cp_dir) == [
        "track-01-ml-programmer/01_a.ipynb"
    ]


def test_real_repo_subset_is_non_empty_and_exists():
    subset = select(ROOT)
    assert subset, "the repo must yield an execution subset"
    assert len(subset) == len(set(subset))
    for rel in subset:
        assert (ROOT / rel).is_file(), f"{rel} does not exist"
