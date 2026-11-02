"""Normalize notebooks to a clean nbformat 4.5 shape.

* Removes keys that do not belong to a cell type (e.g. `execution_count` on
  markdown cells, `outputs` on markdown cells).
* Adds stable cell ids where missing.
* Restores nbformat_minor to 5 so serialized notebooks validate without
  MissingIDFieldWarning.

Safe to re-run: already-normalized notebooks are rewritten identically.
"""
import json
import sys
import uuid
from pathlib import Path

import nbformat

ROOT = Path(__file__).resolve().parent.parent
MARKS = ("value",)


def clean_cell(cell: dict) -> dict:
    cell.setdefault("metadata", {})
    if cell.get("cell_type") == "markdown":
        cell.pop("execution_count", None)
        cell.pop("outputs", None)
    elif cell.get("cell_type") == "code":
        cell.setdefault("execution_count", None)
        cell.setdefault("outputs", [])
    cell.pop("attachments", None) if not cell.get("attachments") else None
    if "id" not in cell:
        cell["id"] = uuid.uuid4().hex[:8]
    if isinstance(cell.get("source"), str):
        cell["source"] = cell["source"].splitlines(keepends=True)
    return cell


def main() -> int:
    changed = 0
    for nb_path in sorted(ROOT.glob("track-*/*.ipynb")):
        raw = json.loads(nb_path.read_text())
        raw.setdefault("metadata", {})
        raw["metadata"].setdefault(
            "kernelspec", {"display_name": "Python 3", "language": "python", "name": "python3"}
        )
        raw["metadata"].setdefault("language_info", {"name": "python"})
        raw.setdefault("nbformat", 4)
        raw.setdefault("nbformat_minor", 5)
        raw["nbformat"] = 4
        raw["nbformat_minor"] = 5
        raw.setdefault("cells", [])

        nb = nbformat.from_dict(raw)
        before = json.dumps(nb, sort_keys=True)
        nb.cells = [nbformat.from_dict(clean_cell(dict(cell))) for cell in nb.cells]

        nbformat.validate(nb)
        after = json.dumps(nb, sort_keys=True)
        if before != after:
            nbformat.write(nb, str(nb_path))
            changed += 1
            print(f"NORMALIZED {nb_path.relative_to(ROOT)}")

    print(f"{changed} notebook(s) normalized")
    return 0


if __name__ == "__main__":
    sys.exit(main())