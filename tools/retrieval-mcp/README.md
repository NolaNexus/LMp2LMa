# Retrieval MCP

Local semantic search over the journey repo. Embeds with LM Studio, reranks with llama.cpp, and exposes the result to OpenCode, Hermes, and Zed over MCP.

## Stack

| Piece | Default | Port |
|---|---|---|
| Embeddings | `text-embedding-qwen3-embedding-0.6b` via LM Studio | `1234` |
| Rerank | `qwen3-reranker-0.6b` via `llama-server --reranking` | `1235` |
| MCP server | `retrieval_mcp.py` (streamable HTTP) | `8765` |

The index is plain JSON plus a NumPy matrix at `artifacts/retrieval/index/` (gitignored). No vector database is required.

## Setup

```bash
cd tools/retrieval-mcp
python3 -m venv --system-site-packages .venv
.venv/bin/pip install -r requirements.txt
```

If `uv` is available, the equivalent is:

```bash
uv venv --system-site-packages .venv
uv pip install --python .venv/bin/python -r requirements.txt
```

## Run

```bash
./services.sh start     # starts rerank + MCP in tmux sessions named rerank, retrieval-mcp
./services.sh status
./services.sh logs
./services.sh stop
```

Build or rebuild the index:

```bash
.venv/bin/python retrieval_mcp.py --reindex --build-only
```

Restart with a forced rebuild:

```bash
./services.sh stop
.venv/bin/python retrieval_mcp.py --reindex --build-only
./services.sh start
```

## Tools

| Tool | Purpose |
|---|---|
| `search(query, k=8, rerank=true)` | Vector top-24, reranked, returns top `k` with path, lines, score, snippet. |
| `fetch(doc_id)` | Full indexed chunk for a `doc_id`. |
| `reindex(paths?)` | Rebuild everything, or only the given repo-relative files/dirs. |
| `stats()` | Chunk/file counts, models, rerank health. |

## Endpoint

```text
http://127.0.0.1:8765/mcp
```

Wiring already applied:

- OpenCode: `~/.config/opencode/opencode.jsonc` → `mcp.retrieval` (`type: remote`)
- Hermes: `hermes mcp add retrieval --url http://127.0.0.1:8765/mcp`
- Zed: `~/.var/app/dev.zed.Zed/config/zed/settings.json` → `context_servers.retrieval`

## Configuration

Override with environment variables:

| Variable | Default |
|---|---|
| `RETRIEVAL_ROOT` | repo root (two levels above this file) |
| `RETRIEVAL_INDEX_DIR` | `artifacts/retrieval/index` |
| `LMSTUDIO_URL` | `http://127.0.0.1:1234/v1` |
| `RETRIEVAL_EMBED_MODEL` | `text-embedding-qwen3-embedding-0.6b` |
| `RERANK_URL` | `http://127.0.0.1:1235/v1` |
| `RETRIEVAL_RERANK_MODEL` | `qwen3-reranker` |
| `RETRIEVAL_TOP_K` | `8` |
| `RETRIEVAL_CANDIDATES` | `12` |
| `RETRIEVAL_RERANK_MAX_CHARS` | `900` |

If rerank is down, `search` still works and falls back to vector scores.

## Notes

- First build embeds ~1,100 chunks and takes several minutes on the local model. Incremental `reindex(paths=[...])` only re-embeds touched files.
- Notebook chunks are cell-aware; code and Markdown cells are indexed separately.
- `start.sh` expects the LM Studio AVX2 `llama-server` build. Override `RERANK_BIN` if your path differs.
- The index is rebuilt if the embedding model changes.
