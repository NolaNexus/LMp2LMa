"""Recover ATT-001 notebooks from the original (invalid-JSON) sources at cc258d9.

The original files contain `"source": [ ... ]` arrays where some elements were
written unquoted with raw newlines. This script scans the raw text, decodes
properly-quoted JSON string elements, and reconstructs unquoted chunks by
accumulating raw lines until the terminating quote, then unescaping.

Output: rewritten notebooks (nbformat 4) at their original paths.
"""
import ast
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

NOTEBOOKS = [
    "track-01-ml-programmer/05_computational_theory.ipynb",
    "track-01-ml-programmer/06_bayesian_methods.ipynb",
    "track-01-ml-programmer/07_reinforcement_learning.ipynb",
    "track-02-dl-programmer/03_rnn_seq.ipynb",
    "track-02-dl-programmer/04_transformers.ipynb",
    "track-02-dl-programmer/09_time_series.ipynb",
    "track-02-dl-programmer/10_recommender_systems.ipynb",
    "track-03-ml-engineer/02_feature_store.ipynb",
    "track-03-ml-engineer/03_mlflow_advanced.ipynb",
    "track-04-ml-architect/02_triton_serving.ipynb",
    "track-04-ml-architect/03_quantization.ipynb",
    "track-04-ml-architect/05_cost_optimization.ipynb",
    "track-04-ml-architect/06_foundation_model_finetune.ipynb",
]

QUOTED_RE = re.compile(r'^\s*("(?:[^"\\]|\\.)*")\s*,?\s*$')


def decode_string_element(line: str) -> str | None:
    m = QUOTED_RE.match(line)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


def unescape_raw(chunk: str) -> str:
    s = chunk.replace('\\"', '"').replace("\\'", "'")
    s = s.replace("\\n", "\n").replace("\\t", "\t").replace("\\\\", "\\")
    return s


def extract_cells(text: str) -> list[dict]:
    lines = text.split("\n")
    cells: list[dict] = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]
        stripped = line.strip()
        if stripped == "{":
            cell_type = None
            exec_count = None
            source = ""
            j = i + 1
            while j < n:
                ln = lines[j]
                st = ln.strip()
                if st.startswith('"cell_type"'):
                    m = QUOTED_RE.match(st.rstrip(","))
                    if not m:
                        m2 = re.match(r'^"cell_type"\s*:\s*("(?:[^"\\]|\\.)*")', st)
                        if m2:
                            cell_type = json.loads(m2.group(1))
                elif st.startswith('"execution_count"'):
                    m = re.match(r'^"execution_count"\s*:\s*(null|\d+)', st)
                    if m:
                        exec_count = None if m.group(1) == "null" else int(m.group(1))
                elif st.startswith('"source"'):
                    # collect array until the matching closing ] at this indent
                    k = j + 1
                    while k < n and lines[k].strip() != "]":
                        elem = decode_string_element(lines[k])
                        if elem is not None:
                            source += elem
                            k += 1
                            continue
                        # single-line raw chunk ending in \n",
                        m = re.match(r'^\s*(.*)\\n"\s*,?\s*$', lines[k])
                        if m:
                            source += unescape_raw(m.group(1)) + "\n"
                            k += 1
                            continue
                        # multi-line raw chunk: accumulate until a bare " line
                        chunk_lines = []
                        while k < n and lines[k].strip() != "]":
                            cur = lines[k]
                            if cur.strip() == '"':
                                k += 1
                                break
                            chunk_lines.append(cur)
                            k += 1
                        if chunk_lines:
                            first = chunk_lines[0]
                            chunk_lines[0] = first.lstrip()
                            source += unescape_raw("\n".join(chunk_lines))
                    j = k
                elif st in ("},", "}"):
                    break
                j += 1

            cells.append(
                {
                    "cell_type": cell_type or "code",
                    "execution_count": exec_count,
                    "source": source,
                }
            )
            i = j
        i += 1

    return cells


def strip_magics(source: str) -> str:
    out = []
    for line in source.splitlines(keepends=True):
        s = line.strip()
        if s.startswith(("!", "%")):
            out.append("pass\n")
        else:
            out.append(line)
    return "".join(out)


def main() -> int:
    failures = []
    for nb_rel in NOTEBOOKS:
        try:
            original = subprocess.run(
                ["git", "show", f"cc258d9:{nb_rel}"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=True,
            ).stdout
        except subprocess.CalledProcessError:
            failures.append(f"{nb_rel}: not found at cc258d9")
            continue

        cells = extract_cells(original)
        rebuilt = {
            "cells": [],
            "metadata": {
                "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                "language_info": {"name": "python"},
            },
            "nbformat": 4,
            "nbformat_minor": 5,
        }

        code_cells = 0
        bad = []
        for ci, cell in enumerate(cells):
            ct = cell["cell_type"]
            src = cell["source"]
            if ct == "code":
                code_cells += 1
                cleaned = strip_magics(src)
                if cleaned.strip():
                    try:
                        ast.parse(cleaned)
                    except SyntaxError as e:
                        bad.append(f"cell_{ci}:{e.lineno}: {e.msg}")

            new_cell = {
                "cell_type": ct,
                "metadata": {},
                "source": src.splitlines(keepends=True),
            }
            if ct == "code":
                new_cell["execution_count"] = None
                new_cell["outputs"] = []
            rebuilt["cells"].append(new_cell)

        if bad:
            failures.append(f"{nb_rel}: {len(bad)} bad code cells -> " + "; ".join(bad[:5]))
        if not cells:
            failures.append(f"{nb_rel}: extraction produced 0 cells")
            continue

        out_path = ROOT / nb_rel
        out_path.write_text(json.dumps(rebuilt, indent=1, ensure_ascii=False) + "\n")
        status = "PARTIAL" if bad else "RECOVERED"
        print(f"{status} {nb_rel}: {len(cells)} cells ({code_cells} code)")

    if failures:
        print("\nFAILURES:", file=sys.stderr)
        for f in failures:
            print(" -", f, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())