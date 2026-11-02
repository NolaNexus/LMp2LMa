---
name: Repo orientation
description: What is in this repository and where — directory structure, track notebooks, tests, tooling, and the commands that prove the tree is healthy. Use when orienting before a change.
status: active
---

# Repo orientation

Use this before any non-trivial change in this workspace. The repository is a
learning workspace (Skillsoft *ML Programmer to ML Architect* journey), not an
application: most of the corpus is notebooks, and the code that exists is
tooling around them.

## Layout

| Path | What it holds |
|---|---|
| `track-01-ml-programmer/` | Foundations track notebooks |
| `track-02-dl-programmer/` | Deep learning track notebooks (in progress) |
| `track-03-ml-engineer/` | MLOps track notebooks |
| `track-04-ml-architect/` | Architecture track notebooks |
| `capstone/` | Capstone deliverables, with its own `AGENTS.md` and `tests/` |
| `dashboard/app.py` | Streamlit progress dashboard |
| `tests/` | Pytest suite; `test_notebooks.py` validates every notebook structurally |
| `tools/` | Repo tooling, including the retrieval MCP |
| `docs/adr/` | Architecture decision records for the skill system itself |
| `artifacts/` | Generated output; gitignored except the directory marker |
| `AGENTS.md` | Root agent guidance, including the model routing table |

`AGENTS.md` is authoritative for agent routing. Do not restate it; read it.

## Order of operations

1. Semantic search first — see the `retrieval-mcp` skill. Grep is the
   fallback for identifiers, not the opening move.
2. Read the specific file the search pointed at.
3. Only then open the tree more widely.

## Health check

```bash
python3 tools/validate_notebooks.py
python3 -m pytest tests -q
ruff check .
```

`validate_notebooks.py` checks JSON integrity, nbformat conformance, and
`ast.parse` on every code cell, reporting `file:cell_index:lineno`. `pytest`
adds the per-track notebook-count minimums (`MINIMUMS` in
`tests/test_notebooks.py`). `ruff` is configured in `pyproject.toml` at line
length 100 with `E`, `F`, `I`.

## Before committing

```bash
pre-commit run --all-files
```

Hooks are `ruff`, `ruff-format`, and `nbstripout` (see `.pre-commit-config.yaml`).

## Don't

- Don't create a module structure that mirrors an older version of `AGENTS.md`
  ("module-01-foundations" and friends). It describes a suggested future
  layout; the real layout is the track directories above.
- Don't add a project-level OpenCode config file to change routing — routing
  already lives in the global config under `~/.config/opencode/`.
- Don't trust `git status` in this tree without reading it: `tools/retrieval-mcp/`
  is intentionally untracked during active work.
- Don't run the full notebook suite as a smoke test; `pytest` markers `notebook`
  and `slow` exist to keep the fast path fast.
