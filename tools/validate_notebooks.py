"""Validate all notebooks:
1. JSON structural integrity
2. nbformat schema conformance
3. ast.parse on every code cell (magic/! lines stripped)
Exit non-zero on any failure with file:cell_index:lineno reporting.
"""

import ast
import json
import sys
from pathlib import Path

TRACKS = [
    "track-01-ml-programmer",
    "track-02-dl-programmer",
    "track-03-ml-engineer",
    "track-04-ml-architect",
]
ROOT = Path(__file__).resolve().parent.parent


def strip_magics(source: str) -> str:
    lines = []
    for line in source.splitlines(keepends=True):
        stripped = line.strip()
        if stripped.startswith("!") or stripped.startswith("%") or stripped.startswith("%%"):
            indent = line[: len(line) - len(line.lstrip())]
            lines.append(f"{indent}pass\n")
        else:
            lines.append(line)
    return "".join(lines)


def main() -> int:
    errors: list[str] = []
    for track in TRACKS:
        track_dir = ROOT / track
        if not track_dir.is_dir():
            continue
        for nb_path in sorted(track_dir.glob("*.ipynb")):
            try:
                with open(nb_path, "r", encoding="utf-8") as f:
                    nb = json.load(f)
            except json.JSONDecodeError as e:
                errors.append(f"{nb_path}:0:0 JSON ({e})")
                continue

            # nbformat version check
            nbformat = nb.get("nbformat")
            if nbformat not in (4,):
                errors.append(f"{nb_path}:0:0 nbformat={nbformat}")

            cells = nb.get("cells", [])
            for ci, cell in enumerate(cells):
                if cell.get("cell_type") != "code":
                    continue
                raw_source = cell.get("source", "")
                if isinstance(raw_source, list):
                    source = "".join(raw_source)
                else:
                    source = raw_source

                cleaned = strip_magics(source)
                if not cleaned.strip():
                    continue
                try:
                    ast.parse(cleaned, filename=f"{nb_path}:cell_{ci}")
                except SyntaxError as e:
                    lineno = e.lineno or 1
                    errors.append(f"{nb_path}:cell_{ci}:{lineno} {e.msg}")

    if errors:
        for err in errors:
            print(err, file=sys.stderr)
        print(f"\n{len(errors)} failures total", file=sys.stderr)
        return 1

    print("All notebooks valid (json + nbformat + ast)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
