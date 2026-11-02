"""Fix code-cell source corruption: unescape `\"` and `\'`, strip trailing artifacts.

Run this after Phase 0. Validates with ast.parse after each fix.
"""
import ast
import json
import re
import sys
from pathlib import Path

import nbformat

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
            lines.append("pass\n")
        else:
            lines.append(line)
    return "".join(lines)


def unescape_source(source: str) -> str:
    """Replace `\"` with `"`, `\'` with `'`, remove stray `n` at line starts after `\n`.
    Then strip trailing `,` that was a JSON remnant.
    """
    # Replace escaped quotes
    s = source.replace('\\"', '"').replace("\\'", "'")
    # Fix stray `\n,` at line boundaries (the `,` remnant from rebuild)
    s = re.sub(r'\n",', '\n', s)
    # Fix stray `n` at line starts (from `\n` becoming bare text)
    s = re.sub(r'(?<=\n)n', '', s)
    # Also fix bare `n` at the very start
    if s.startswith('n') and len(s) > 1 and s[1] not in (' ', "'"):
        s = s[1:]
    return s


def cell_source(nb: dict, ci: int) -> str:
    cell = nb["cells"][ci]
    raw = cell.get("source", "")
    if isinstance(raw, list):
        return "".join(raw)
    return raw


def set_cell_source(nb: dict, ci: int, new_source: str):
    cell = nb["cells"][ci]
    # Store as a list of lines so diff is readable
    lines = new_source.splitlines(keepends=True)
    cell["source"] = lines


def main() -> int:
    fixed_count = 0
    for track in TRACKS:
        track_dir = ROOT / track
        if not track_dir.is_dir():
            continue
        for nb_path in sorted(track_dir.glob("*.ipynb")):
            nb = nbformat.read(nb_path, as_version=4)
            changed = False
            for ci, cell in enumerate(nb.cells):
                if cell.get("cell_type") != "code":
                    continue
                source = cell_source(nb, ci)
                fixed = unescape_source(source)
                if fixed == source:
                    continue

                cleaned = strip_magics(fixed)
                if cleaned.strip():
                    try:
                        ast.parse(cleaned, filename=f"{nb_path}:cell_{ci}")
                    except SyntaxError:
                        # unescaping wasn't enough; skip for manual fix
                        print(f"SKIP (still broken):{nb_path}:cell_{ci}", file=sys.stderr)
                        continue

                set_cell_source(nb, ci, fixed)
                changed = True
                fixed_count += 1

            if changed:
                nbformat.write(nb, nb_path)
                print(f"FIXED {nb_path}: {changed} cells")

    # Final validation pass
    errors = 0
    for track in TRACKS:
        track_dir = ROOT / track
        if not track_dir.is_dir():
            continue
        for nb_path in sorted(track_dir.glob("*.ipynb")):
            with open(nb_path, "r", encoding="utf-8") as f:
                try:
                    nb = json.load(f)
                except json.JSONDecodeError as e:
                    print(f"JSON ERROR:{nb_path}: {e}", file=sys.stderr)
                    errors += 1
                    continue
            for ci, cell in enumerate(nb.get("cells", [])):
                if cell.get("cell_type") != "code":
                    continue
                source = cell_source(nb, ci)
                cleaned = strip_magics(source)
                if not cleaned.strip():
                    continue
                try:
                    ast.parse(cleaned, filename=f"{nb_path}:cell_{ci}")
                except SyntaxError as e:
                    lineno = e.lineno or 1
                    print(f"REMAINING ERROR:{nb_path}:cell_{ci}:{lineno} {e.msg}", file=sys.stderr)
                    errors += 1

    print(f"\nFixed cells: {fixed_count}, remaining errors: {errors}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())