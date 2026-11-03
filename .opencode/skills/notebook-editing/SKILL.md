---
name: Notebook editing
description: Edit, add, or validate a Jupyter notebook under track-*, capstone, or dashboard — cell normalization, nbformat validation, and the execution artifacts that must never be committed.
status: active
---

# Notebook editing

Use when creating, editing, or repairing any `.ipynb` in this repository.

## Editing rules

- Read the notebook as JSON, or with `nbformat`. Never patch notebook JSON
  with `sed` or a line-based editor — a single misplaced comma corrupts the
  file and the failure is silent until validation.
- Preserve existing cell IDs. `tools/normalize_notebooks.py` adds missing ones
  and restores `nbformat_minor` to 5.
- Markdown cells must not carry `execution_count` or `outputs`; code cells
  keep them until strip.

## Repair sequence

```bash
python3 tools/normalize_notebooks.py
python3 tools/validate_notebooks.py
python3 -m pytest tests/test_notebooks.py -q
```

Run them in that order. `normalize_notebooks.py` is idempotent — re-running it
on a normalized notebook rewrites it identically, so a diff after the second
run means real drift.

## What validation actually checks

`tools/validate_notebooks.py` reports `file:cell_index:lineno` and exits
non-zero on:

1. JSON structural integrity
2. nbformat schema conformance
3. `ast.parse` on every code cell, with `!`/`%`/`%%` lines replaced by `pass`

`tests/test_notebooks.py` additionally enforces per-track notebook minimums
(`MINIMUMS`). Adding a notebook below a minimum is fine; deleting one is not.

## Outputs and artifacts

- `nbstripout` runs as a pre-commit hook and removes outputs on commit.
  Do not commit a notebook with outputs by bypassing it.
- `execution_count` values that survive into a diff mean the hook was skipped.

## Don't

- Don't execute every notebook to check your change. Use the fast structural
  tests; `pytest --nbval-lax` is reserved for the CI fast subset described in
  `.github/workflows/assessment.yml`.
- Don't renumber or delete cells to make a diff smaller — cell order is the
  lesson order, and the grader counts them.
- Don't write a cell that only runs on the Maxwell GPU host. See the
  `requirements-gpu-cu126.txt` header for the limits (`TORCHDYNAMO_DISABLE=1`,
  no bf16, no FlashAttention).
- Don't add a notebook to a track without checking `tests/conftest.py` for the
  registered markers first.
