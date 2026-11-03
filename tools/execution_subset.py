"""Derive the CI execution subset from the repo instead of hardcoding it (A2).

The workflow executes a small set of notebooks on every push: enough to prove
the assessment pipeline is wired end to end, not enough to need a GPU or a
network download. That set used to be a literal list in `tests/run_assessment.py`
and in the workflow, so adding or renaming a notebook silently left CI running a
stale list.

Policy:

* only tracks whose `STATUS.md` rows are fully green are eligible; unmeasured
  tracks join automatically once a sweep records them (`--all-tracks` overrides);
* one entry per track, taken in the order the track's checkpoints declare
  (falling back to filename order when a checkpoint file is missing);
* `--per-track` notebooks per track (default 2: the introductory notebooks);
* a notebook that no longer exists on disk is skipped, so a rename in the
  checkpoint file propagates here without editing this file.

The output is the relative path of each notebook, one per line by default.

Usage:
    python tools/execution_subset.py                       # lines
    python tools/execution_subset.py --format json
    python tools/execution_subset.py --per-track 3
"""

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHECKPOINT_DIR = ROOT / "checkpoints"

# | track-01-ml-programmer | 7 | 7 | 7 | 0 |
_TRACK_ROW_RE = re.compile(
    r"^\|\s*(track-[\w-]+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|", re.MULTILINE
)

# Checkpoint filenames are track ids with underscores; directory names use hyphens.
TRACK_CHECKPOINTS = {
    "track-01-ml-programmer": "track_01_ml_programmer.json",
    "track-02-dl-programmer": "track_02_dl_programmer.json",
    "track-03-ml-engineer": "track_03_ml_engineer.json",
    "track-04-ml-architect": "track_04_ml_architect.json",
}


def track_dirs(root: Path = ROOT) -> list[Path]:
    return sorted(p for p in root.glob("track-*") if p.is_dir())


def checkpoint_order(track: Path, checkpoint_dir: Path = CHECKPOINT_DIR) -> list[str]:
    """Notebook filenames in checkpoint order, or [] when no checkpoint exists."""
    path = checkpoint_dir / TRACK_CHECKPOINTS.get(track.name, f"{track.name}.json")
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    return [cp.get("notebook", "") for cp in data.get("checkpoints", []) if cp.get("notebook")]


def measured_green_tracks(root: Path = ROOT) -> set[str] | None:
    """Tracks whose every measured notebook passed, from the generated STATUS.md.

    Returns None when no measurement is available, which makes the caller
    consider every track. STATUS.md is generated (`tools/status_report.py`) and
    committed, so CI can derive the subset from the same truth the docs do.
    """
    status = root / "STATUS.md"
    if not status.exists():
        return None
    rows = _TRACK_ROW_RE.findall(status.read_text(encoding="utf-8"))
    if not rows:
        return None
    return {
        name for name, _count, executed, passed in rows if int(executed) > 0 and executed == passed
    }


def select(
    root: Path = ROOT,
    per_track: int = 2,
    tracks: list[str] | None = None,
    checkpoint_dir: Path = CHECKPOINT_DIR,
    measured_only: bool = True,
) -> list[str]:
    """Return relative paths of the notebooks the fast gate should execute.

    With `measured_only`, only tracks that STATUS.md reports as fully green are
    eligible. If nothing has been measured yet, every track is considered so
    the gate cannot silently shrink to nothing.
    """
    if per_track < 0:
        raise ValueError("per_track must be >= 0")

    eligible = set(tracks) if tracks else None
    if eligible is None and measured_only:
        eligible = measured_green_tracks(root)
        if not eligible:
            eligible = None  # no measurement -> every track

    chosen: list[str] = []
    for track in track_dirs(root):
        if eligible is not None and track.name not in eligible:
            continue
        on_disk = {p.name for p in track.glob("*.ipynb") if not p.name.startswith(".")}
        ordered = [name for name in checkpoint_order(track, checkpoint_dir) if name in on_disk]
        # Any notebook the checkpoints do not mention stays reachable via filename order.
        ordered += sorted(on_disk - set(ordered))
        for name in ordered[:per_track]:
            chosen.append(str((track / name).relative_to(root)))
    return chosen


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--per-track", type=int, default=2, help="notebooks per track (default 2)")
    parser.add_argument(
        "--format", choices=("lines", "json"), default="lines", help="output format"
    )
    parser.add_argument(
        "--root", type=Path, default=ROOT, help="repo root to derive the subset from"
    )
    parser.add_argument(
        "--track", action="append", dest="tracks", help="restrict to one track (repeatable)"
    )
    parser.add_argument(
        "--all-tracks",
        action="store_true",
        help="ignore STATUS.md and consider every track, measured or not",
    )
    args = parser.parse_args(argv)

    subset = select(
        root=args.root,
        per_track=args.per_track,
        tracks=args.tracks,
        measured_only=not args.all_tracks,
    )
    if args.format == "json":
        print(json.dumps(subset, indent=2))
    else:
        print("\n".join(subset))
    return 0


if __name__ == "__main__":
    sys.exit(main())
