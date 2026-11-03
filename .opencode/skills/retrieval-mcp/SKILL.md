---
name: Retrieval MCP
description: Find things in this repository with the local semantic retrieval MCP — search, fetch, reindex, and the services.sh lifecycle — instead of starting with grep.
status: active
---

# Retrieval MCP

Use when you need to locate a concept, notebook section, or piece of code
anywhere in the repository. Semantic search finds things whose wording you do
not know; grep only finds what you already named correctly.

## Tools

The `retrieval` MCP server exposes four tools.

| Tool | Use |
|---|---|
| `search(query, k=8, rerank=True, paths=None)` | Natural-language query; returns ranked hits with `doc_id`, `path`, line range, score |
| `fetch(doc_id)` | Full text of one hit |
| `reindex(paths=None)` | Rebuild the whole index, or only the given repo-relative paths |
| `stats()` | Chunk count, file count, embedding and rerank model names |

Typical loop: `search` → pick by `path` and line range → `fetch` the one you
need. Do not `fetch` every hit.

## Scoping a search

Pass `paths` to restrict the candidate set before ranking:

```
search(query="add a notebook to track-02", paths=[".opencode/skills"])
```

Skill routing uses this: the four skills are indexed as documents, and their
routing is measured by `tools/skills_routing_eval.py`. Scores are rerank
probabilities, so they are meaningful in absolute terms — a skill scoring
below 0.5 is not a match, and loading it anyway is the over-triggering failure
mode this threshold guards against.

## After you edit files

Reindex the paths you touched, not the whole tree:

```
reindex(paths=["track-03-ml-engineer/02_feature_store.ipynb"])
```

Full rebuilds are for schema or model changes.

## Service lifecycle

The stack runs in tmux: rerank on `127.0.0.1:1235`, MCP on
`http://127.0.0.1:8765/mcp`, embeddings from LM Studio on
`127.0.0.1:1234`. Manage it with:

```bash
tools/retrieval-mcp/services.sh status
tools/retrieval-mcp/services.sh start
tools/retrieval-mcp/services.sh logs
```

`start` warns but continues if LM Studio is down; embeddings will then fail
on first use. `logs` tails both the rerank and MCP logs.

## What is indexed

`.md`, `.mdx`, `.ipynb`, and `.py` under the repository root, excluding
`.git`, `.venv`, `node_modules`, `__pycache__`, `.ipynb_checkpoints`, and the
pytest/mypy/ruff caches. Notebooks are indexed by code and markdown source,
not by outputs. The index lives in `artifacts/retrieval/index/` and is
gitignored.

## Don't

- Don't use `search` for an exact identifier you already know —
  `grep -rn "SymbolName"` is cheaper and exact.
- Don't run `reindex(paths=None)` after a single file edit; it re-embeds
  everything and blocks the server.
- Don't point `RETRIEVAL_ROOT` at a different tree to "search elsewhere" — the
  index is a property of this repository and mixing roots corrupts the store.
- Don't start the service with `python retrieval_mcp.py` from the wrong venv.
  The interpreter is `tools/retrieval-mcp/.venv/bin/python`; the root `.venv`
  does not exist.
