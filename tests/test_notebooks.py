"""Structural validation tests for every notebook.

Fast tests (default):
  * JSON parse and nbformat schema validation
  * ast.parse on every code cell, with IPython magics neutralised

Notebook *execution* is covered separately by `pytest --nbval-lax` on the fast
subset (see .github/workflows/assessment.yml) and by the grader.
"""
import ast
import json
from pathlib import Path

import nbformat
import pytest

ROOT = Path(__file__).resolve().parents[1]
TRACKS = [
    "track-01-ml-programmer",
    "track-02-dl-programmer",
    "track-03-ml-engineer",
    "track-04-ml-architect",
]

MINIMUMS = {
    "track-01-ml-programmer": 7,
    "track-02-dl-programmer": 11,
    "track-03-ml-engineer": 8,
    "track-04-ml-architect": 12,
}

NOTEBOOKS = sorted(
    p for track in TRACKS for p in (ROOT / track).glob("*.ipynb") if not p.name.startswith(".")
)


def strip_magics(source: str) -> str:
    """Replace IPython magics/shell escapes with `pass`, preserving indentation."""
    lines = []
    for line in source.splitlines(keepends=True):
        stripped = line.strip()
        if stripped.startswith(("!", "%", "%%")):
            indent = line[: len(line) - len(line.lstrip())]
            lines.append(f"{indent}pass\n")
        else:
            lines.append(line)
    return "".join(lines)


def notebook_id(path: Path) -> str:
    return str(path.relative_to(ROOT))


@pytest.mark.notebook
@pytest.mark.parametrize("nb_path", NOTEBOOKS, ids=notebook_id)
def test_notebook_json_and_schema(nb_path: Path):
    """Every notebook must be valid JSON and conform to nbformat 4."""
    with open(nb_path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    assert raw.get("nbformat") == 4, f"unexpected nbformat: {raw.get('nbformat')}"

    nb = nbformat.read(nb_path, as_version=4)
    nbformat.validate(nb)


@pytest.mark.notebook
@pytest.mark.parametrize("nb_path", NOTEBOOKS, ids=notebook_id)
def test_notebook_code_cells_parse(nb_path: Path):
    """Every code cell must parse as Python after magic neutralisation."""
    nb = nbformat.read(nb_path, as_version=4)
    for ci, cell in enumerate(nb.cells):
        if cell.cell_type != "code":
            continue
        cleaned = strip_magics(cell.source)
        if not cleaned.strip():
            continue
        try:
            ast.parse(cleaned, filename=f"{nb_path.name}:cell_{ci}")
        except SyntaxError as exc:
            pytest.fail(f"{notebook_id(nb_path)} cell_{ci} line {exc.lineno}: {exc.msg}")


@pytest.mark.notebook
def test_notebook_count():
    """Each track must keep at least the agreed notebook count."""
    counts = {}
    for nb in NOTEBOOKS:
        track = nb.relative_to(ROOT).parts[0]
        counts[track] = counts.get(track, 0) + 1

    shortfalls = [
        f"{track}: {counts.get(track, 0)} < {minimum}"
        for track, minimum in MINIMUMS.items()
        if counts.get(track, 0) < minimum
    ]
    assert not shortfalls, "; ".join(shortfalls)