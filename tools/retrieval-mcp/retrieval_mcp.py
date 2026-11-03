#!/usr/bin/env python3
"""Local retrieval MCP server for the ML Architect journey repository.

Indexes Markdown, notebooks, and Python files, embeds them with a local
LM Studio embedding model, and reranks results with a local llama.cpp
reranker. Exposes `search`, `fetch`, `reindex`, and `stats` over MCP.

Run:
    .venv/bin/python retrieval_mcp.py --reindex
    .venv/bin/python retrieval_mcp.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import threading
import time
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import requests
from mcp.server.mcpserver import MCPServer

LOG = logging.getLogger("retrieval-mcp")

REPO_ROOT = Path(os.environ.get("RETRIEVAL_ROOT", Path(__file__).resolve().parents[2])).resolve()
INDEX_DIR = Path(
    os.environ.get("RETRIEVAL_INDEX_DIR", REPO_ROOT / "artifacts" / "retrieval" / "index")
).resolve()

LMSTUDIO_URL = os.environ.get("LMSTUDIO_URL", "http://127.0.0.1:1234/v1").rstrip("/")
EMBED_MODEL = os.environ.get("RETRIEVAL_EMBED_MODEL", "text-embedding-qwen3-embedding-0.6b")
RERANK_URL = os.environ.get("RERANK_URL", "http://127.0.0.1:1235/v1").rstrip("/")
RERANK_MODEL = os.environ.get("RETRIEVAL_RERANK_MODEL", "qwen3-reranker")
TOP_K = int(os.environ.get("RETRIEVAL_TOP_K", "8"))
CANDIDATES = int(os.environ.get("RETRIEVAL_CANDIDATES", "12"))
RERANK_MAX_CHARS = int(os.environ.get("RETRIEVAL_RERANK_MAX_CHARS", "900"))
BATCH_SIZE = int(os.environ.get("RETRIEVAL_EMBED_BATCH", "24"))

TEXT_EXTS = {".md", ".mdx", ".ipynb", ".py"}
SKIP_PARTS = {
    ".git",
    ".venv",
    "node_modules",
    "__pycache__",
    ".ipynb_checkpoints",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".archive",
}
MAX_FILE_BYTES = 2_000_000
MAX_CHUNK_CHARS = 1500
OVERLAP_CHARS = 200

QUERY_INSTRUCTION = (
    "Instruct: Given a search query, retrieve relevant passages from a machine "
    "learning engineering repository containing notebooks, documentation, and code.\n"
    "Query: "
)

mcp = MCPServer(
    name="retrieval",
    title="Local retrieval",
    version="0.1.0",
    instructions=(
        "Search this repository semantically. Use `search` to find relevant "
        "notebook sections, docs, or code, then `fetch` a doc_id for the full "
        "chunk. Use `reindex` after large edits."
    ),
)


# ---------------------------------------------------------------------------
# Index storage
# ---------------------------------------------------------------------------


def _hash(text: str, length: int = 16) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:length]


def _path_matches(path: str, patterns: list[str]) -> bool:
    """True when a repo-relative path matches any prefix or glob pattern."""
    for raw in patterns:
        pattern = raw.strip().strip("/")
        if not pattern:
            continue
        if path == pattern or fnmatch(path, pattern):
            return True
        if path.startswith(pattern + "/"):
            return True
    return False


def _iter_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if any(part in SKIP_PARTS for part in rel.parts):
            continue
        if path.suffix.lower() not in TEXT_EXTS:
            continue
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                LOG.info("skip large file: %s", rel)
                continue
        except OSError:
            continue
        yield path


def _split_text(text: str, limit: int = MAX_CHUNK_CHARS, overlap: int = OVERLAP_CHARS) -> list[str]:
    text = text.strip()
    if len(text) <= limit:
        return [text] if text else []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + limit, len(text))
        if end < len(text):
            boundary = text.rfind("\n\n", start + limit // 2, end)
            if boundary == -1:
                boundary = text.rfind("\n", start + limit // 2, end)
            if boundary != -1:
                end = boundary
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks


def _markdown_chunks(rel: str, text: str) -> list[dict[str, Any]]:
    lines = text.splitlines()
    sections: list[tuple[str, int, list[str]]] = []
    title = rel
    heading = ""
    start = 1
    body: list[str] = []

    def flush() -> None:
        nonlocal body
        if body and any(line.strip() for line in body):
            sections.append((heading or title, start, body))
        body = []

    for lineno, line in enumerate(lines, start=1):
        match = re.match(r"^(#{1,6})\s+(.*)$", line)
        if match:
            flush()
            heading = match.group(2).strip()
            if match.group(1) == "#":
                title = heading
            start = lineno
            body = [line]
        else:
            body.append(line)
    flush()

    chunks: list[dict[str, Any]] = []
    for section_title, section_start, section_lines in sections:
        section_text = "\n".join(section_lines).strip()
        for index, piece in enumerate(_split_text(section_text)):
            chunks.append(
                {
                    "path": rel,
                    "start_line": section_start,
                    "end_line": section_start + len(section_lines) - 1,
                    "kind": "markdown",
                    "title": section_title,
                    "text": piece,
                    "doc_id": _hash(f"{rel}:{section_start}:{index}:{piece[:64]}"),
                }
            )
    return chunks


def _notebook_chunks(rel: str, text: str) -> list[dict[str, Any]]:
    try:
        notebook = json.loads(text)
    except json.JSONDecodeError:
        return _plain_chunks(rel, text, "notebook")

    title = rel
    for cell in notebook.get("cells", []):
        if cell.get("cell_type") == "markdown":
            source = "".join(cell.get("source", []))
            match = re.search(r"^#\s+(.+)$", source, re.MULTILINE)
            if match:
                title = match.group(1).strip()
                break

    chunks: list[dict[str, Any]] = []
    for cell_index, cell in enumerate(notebook.get("cells", [])):
        source = "".join(cell.get("source", [])).strip()
        if not source:
            continue
        cell_type = cell.get("cell_type", "code")
        if cell_type == "markdown":
            prefix = f"Notebook: {rel}\nSection: {title}\n"
        else:
            prefix = f"Notebook: {rel}\nCode cell {cell_index}\n"
        for index, piece in enumerate(_split_text(source)):
            chunks.append(
                {
                    "path": rel,
                    "start_line": 0,
                    "end_line": 0,
                    "kind": "notebook",
                    "title": f"{title} (cell {cell_index}, {cell_type})",
                    "text": prefix + piece,
                    "doc_id": _hash(f"{rel}:cell{cell_index}:{index}:{piece[:64]}"),
                }
            )
    return chunks


def _plain_chunks(rel: str, text: str, kind: str) -> list[dict[str, Any]]:
    lines = text.splitlines()
    chunks: list[dict[str, Any]] = []
    index = 0
    step = 60
    overlap = 8
    start = 0
    while start < len(lines):
        end = min(start + step, len(lines))
        body = "\n".join(lines[start:end]).strip()
        if body:
            chunks.append(
                {
                    "path": rel,
                    "start_line": start + 1,
                    "end_line": end,
                    "kind": kind,
                    "title": rel,
                    "text": f"File: {rel}\n{body}",
                    "doc_id": _hash(f"{rel}:{start}:{index}:{body[:64]}"),
                }
            )
        if end >= len(lines):
            break
        start = max(end - overlap, start + 1)
        index += 1
    return chunks


def _chunks_for_file(path: Path) -> list[dict[str, Any]]:
    rel = path.relative_to(REPO_ROOT).as_posix()
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        LOG.warning("read failed for %s: %s", rel, exc)
        return []
    suffix = path.suffix.lower()
    if suffix in {".md", ".mdx"}:
        return _markdown_chunks(rel, text)
    if suffix == ".ipynb":
        return _notebook_chunks(rel, text)
    return _plain_chunks(rel, text, "python")


# ---------------------------------------------------------------------------
# Embedding and rerank clients
# ---------------------------------------------------------------------------


def _post_json(url: str, payload: dict[str, Any], timeout: int = 180) -> dict[str, Any]:
    response = requests.post(url, json=payload, timeout=timeout)
    response.raise_for_status()
    return response.json()


def _embed(texts: list[str]) -> np.ndarray:
    vectors: list[list[float]] = []
    for start in range(0, len(texts), BATCH_SIZE):
        batch = texts[start : start + BATCH_SIZE]
        try:
            payload = _post_json(
                f"{LMSTUDIO_URL}/embeddings",
                {"model": EMBED_MODEL, "input": batch},
            )
        except requests.RequestException as exc:
            if len(batch) == 1:
                raise
            LOG.warning("embedding batch failed (%s); splitting in half", exc)
            half = max(1, len(batch) // 2)
            vectors.extend(_embed(batch[:half]).tolist())
            vectors.extend(_embed(batch[half:]).tolist())
            continue
        data = sorted(payload.get("data", []), key=lambda item: item.get("index", 0))
        if len(data) != len(batch):
            raise RuntimeError(f"embedding count mismatch: sent {len(batch)}, got {len(data)}")
        vectors.extend(item["embedding"] for item in data)
    array = np.asarray(vectors, dtype=np.float32)
    norms = np.linalg.norm(array, axis=1, keepdims=True)
    return array / np.maximum(norms, 1e-12)


def _rerank(query: str, documents: list[str]) -> list[float] | None:
    if not documents:
        return []
    try:
        payload = _post_json(
            f"{RERANK_URL}/rerank",
            {
                "model": RERANK_MODEL,
                "query": query,
                "documents": [document[:RERANK_MAX_CHARS] for document in documents],
                "top_n": len(documents),
            },
            timeout=120,
        )
    except requests.RequestException as exc:
        LOG.warning("rerank unavailable, falling back to vector scores: %s", exc)
        return None
    results = payload.get("results", [])
    scores = [0.0] * len(documents)
    for item in results:
        index = item.get("index")
        if isinstance(index, int) and 0 <= index < len(scores):
            scores[index] = float(item.get("relevance_score", 0.0))
    return scores


def _rerank_available() -> bool:
    try:
        response = requests.get(f"{RERANK_URL}/health", timeout=2)
        return response.ok
    except requests.RequestException:
        return False


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------


@dataclass
class SearchHit:
    doc_id: str
    path: str
    title: str
    kind: str
    start_line: int
    end_line: int
    score: float
    vector_score: float
    snippet: str


class Store:
    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.chunks: list[dict[str, Any]] = []
        self.embeddings: np.ndarray | None = None
        self.manifest: dict[str, Any] = {}
        self.loaded = False

    # -- persistence --------------------------------------------------------

    @property
    def chunks_path(self) -> Path:
        return INDEX_DIR / "chunks.json"

    @property
    def embeddings_path(self) -> Path:
        return INDEX_DIR / "embeddings.npy"

    @property
    def manifest_path(self) -> Path:
        return INDEX_DIR / "manifest.json"

    def _load(self) -> bool:
        if not (
            self.chunks_path.exists()
            and self.embeddings_path.exists()
            and self.manifest_path.exists()
        ):
            return False
        try:
            self.chunks = json.loads(self.chunks_path.read_text("utf-8"))
            self.embeddings = np.load(self.embeddings_path)
            self.manifest = json.loads(self.manifest_path.read_text("utf-8"))
        except (OSError, ValueError) as exc:
            LOG.warning("index load failed: %s", exc)
            return False
        if self.manifest.get("embed_model") != EMBED_MODEL:
            LOG.info("embedding model changed; rebuild required")
            return False
        if len(self.chunks) != len(self.embeddings):
            LOG.warning("index size mismatch; rebuild required")
            return False
        self.loaded = True
        return True

    def _save(self) -> None:
        INDEX_DIR.mkdir(parents=True, exist_ok=True)
        self.chunks_path.write_text(json.dumps(self.chunks, ensure_ascii=False, indent=1), "utf-8")
        np.save(self.embeddings_path, self.embeddings)
        self.manifest["built_at"] = int(time.time())
        self.manifest["count"] = len(self.chunks)
        self.manifest["dim"] = (
            int(self.embeddings.shape[1])
            if self.embeddings is not None and self.embeddings.size
            else 0
        )
        self.manifest_path.write_text(json.dumps(self.manifest, indent=2), "utf-8")

    # -- build --------------------------------------------------------------

    def ensure_index(self, force: bool = False) -> None:
        with self.lock:
            if not force and self._load():
                LOG.info("index loaded: %d chunks", len(self.chunks))
                return
            self.reindex()

    def reindex(self, paths: list[str] | None = None) -> dict[str, Any]:
        with self.lock:
            if not self.loaded and not self.manifest:
                self._load()

            if paths:
                targets = self._resolve_paths(paths)
            else:
                targets = list(_iter_files(REPO_ROOT))

            target_rels = {path.relative_to(REPO_ROOT).as_posix() for path in targets}
            LOG.info("indexing %d file(s)", len(targets))

            keep_chunks: list[dict[str, Any]] = []
            keep_rows: list[int] = []
            if self.loaded and self.embeddings is not None and target_rels:
                for row, chunk in enumerate(self.chunks):
                    if chunk["path"] not in target_rels:
                        keep_chunks.append(chunk)
                        keep_rows.append(row)

            new_chunks: list[dict[str, Any]] = []
            for path in targets:
                new_chunks.extend(_chunks_for_file(path))

            all_chunks = keep_chunks + new_chunks
            if not all_chunks:
                self.chunks = []
                self.embeddings = np.zeros((0, 0), dtype=np.float32)
                self.manifest = {
                    "root": str(REPO_ROOT),
                    "embed_model": EMBED_MODEL,
                    "files": 0,
                }
                self.loaded = True
                self._save()
                return {"chunks": 0, "files": 0, "indexed": 0}

            if keep_rows and self.embeddings is not None:
                kept_embeddings = self.embeddings[keep_rows]
            else:
                kept_embeddings = np.zeros(
                    (
                        0,
                        self.embeddings.shape[1]
                        if self.embeddings is not None and self.embeddings.size
                        else 0,
                    ),
                    dtype=np.float32,
                )

            new_embeddings = (
                _embed([chunk["text"] for chunk in new_chunks])
                if new_chunks
                else np.zeros(
                    (0, kept_embeddings.shape[1] if kept_embeddings.size else 0), dtype=np.float32
                )
            )

            if kept_embeddings.size and new_embeddings.size:
                self.embeddings = np.vstack([kept_embeddings, new_embeddings])
            elif kept_embeddings.size:
                self.embeddings = kept_embeddings
            elif new_embeddings.size:
                self.embeddings = new_embeddings
            else:
                self.embeddings = np.zeros((0, 0), dtype=np.float32)

            self.chunks = all_chunks
            self.manifest = {
                "root": str(REPO_ROOT),
                "embed_model": EMBED_MODEL,
                "rerank_model": RERANK_MODEL,
                "files": len({chunk["path"] for chunk in all_chunks}),
            }
            self.loaded = True
            self._save()
            LOG.info(
                "index saved: %d chunks from %d files",
                len(self.chunks),
                self.manifest["files"],
            )
            return {
                "chunks": len(self.chunks),
                "files": self.manifest["files"],
                "indexed": len(targets),
                "added_chunks": len(new_chunks),
            }

    def _resolve_paths(self, paths: list[str]) -> list[Path]:
        resolved: set[Path] = set()
        for raw in paths:
            candidate = (REPO_ROOT / raw).resolve()
            if candidate.is_file():
                if candidate.suffix.lower() in TEXT_EXTS:
                    resolved.add(candidate)
            elif candidate.is_dir():
                resolved.update(_iter_files(candidate))
        return sorted(resolved)

    # -- query --------------------------------------------------------------

    def search(
        self,
        query: str,
        k: int = TOP_K,
        rerank: bool = True,
        paths: list[str] | None = None,
    ) -> list[SearchHit]:
        query = query.strip()
        if not query:
            return []
        with self.lock:
            if not self.loaded:
                self.ensure_index()
            if not self.chunks or self.embeddings is None or not self.embeddings.size:
                return []

            query_vector = _embed([QUERY_INSTRUCTION + query])[0]
            similarities = self.embeddings @ query_vector
            if paths:
                allowed = np.array([_path_matches(chunk["path"], paths) for chunk in self.chunks])
                if not allowed.any():
                    return []
                similarities = np.where(allowed, similarities, -np.inf)
            candidate_count = min(max(CANDIDATES, k), len(self.chunks))
            candidate_rows = np.argsort(-similarities)[:candidate_count]
            candidates = [self.chunks[row] for row in candidate_rows]
            if paths:
                candidates = [chunk for chunk in candidates if _path_matches(chunk["path"], paths)]
                candidate_rows = candidate_rows[: len(candidates)]
            if not candidates:
                return []
            vector_scores = [float(similarities[row]) for row in candidate_rows]
            rerank_scores = (
                _rerank(query, [chunk["text"] for chunk in candidates]) if rerank else None
            )

            hits: list[SearchHit] = []
            for position, chunk in enumerate(candidates):
                score = (
                    rerank_scores[position]
                    if rerank_scores is not None
                    else vector_scores[position]
                )
                hits.append(
                    SearchHit(
                        doc_id=chunk["doc_id"],
                        path=chunk["path"],
                        title=chunk.get("title", ""),
                        kind=chunk.get("kind", ""),
                        start_line=int(chunk.get("start_line", 0)),
                        end_line=int(chunk.get("end_line", 0)),
                        score=round(float(score), 6),
                        vector_score=round(vector_scores[position], 6),
                        snippet=chunk["text"][:900],
                    )
                )
            hits.sort(key=lambda hit: hit.score, reverse=True)
            return hits[:k]

    def fetch(self, doc_id: str) -> dict[str, Any] | None:
        with self.lock:
            if not self.loaded:
                self.ensure_index()
            for chunk in self.chunks:
                if chunk["doc_id"] == doc_id:
                    return chunk
        return None

    def stats(self) -> dict[str, Any]:
        with self.lock:
            if not self.loaded:
                self.ensure_index()
            paths = {chunk["path"] for chunk in self.chunks}
            return {
                "root": str(REPO_ROOT),
                "index_dir": str(INDEX_DIR),
                "chunks": len(self.chunks),
                "files": len(paths),
                "embed_model": EMBED_MODEL,
                "rerank_model": RERANK_MODEL,
                "rerank_available": _rerank_available(),
                "built_at": self.manifest.get("built_at"),
            }


STORE = Store()


# ---------------------------------------------------------------------------
# MCP tools
# ---------------------------------------------------------------------------


@mcp.tool()
def search(
    query: str,
    k: int = TOP_K,
    rerank: bool = True,
    paths: list[str] | None = None,
) -> dict[str, Any]:
    """Semantic search over repository docs, notebooks, and code.

    Args:
        query: Natural-language search query.
        k: Number of results to return.
        rerank: Rerank vector candidates with the local Qwen3 reranker.
        paths: Optional repo-relative path prefixes or globs to restrict the
            candidate set, e.g. [".opencode/skills"] to search skills only.
    """
    hits = STORE.search(query, k=k, rerank=rerank, paths=paths)
    return {
        "query": query,
        "count": len(hits),
        "results": [hit.__dict__ for hit in hits],
    }


@mcp.tool()
def fetch(doc_id: str) -> dict[str, Any]:
    """Return the full indexed chunk for a doc_id from a search result."""
    chunk = STORE.fetch(doc_id)
    if chunk is None:
        return {"found": False, "doc_id": doc_id}
    return {"found": True, **chunk}


@mcp.tool()
def reindex(paths: list[str] | None = None) -> dict[str, Any]:
    """Rebuild the index, or only the given repo-relative files/directories."""
    return STORE.reindex(paths)


@mcp.tool()
def stats() -> dict[str, Any]:
    """Report index size, models, and rerank availability."""
    return STORE.stats()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--transport",
        default="streamable-http",
        choices=["streamable-http", "stdio"],
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--path", default="/mcp")
    parser.add_argument("--reindex", action="store_true")
    parser.add_argument("--build-only", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    STORE.ensure_index(force=args.reindex)
    if args.build_only:
        print(json.dumps(STORE.stats(), indent=2))
        return
    LOG.info(
        "serving MCP on http://%s:%d%s (root=%s)",
        args.host,
        args.port,
        args.path,
        REPO_ROOT,
    )
    mcp.run(
        transport=args.transport,
        host=args.host,
        port=args.port,
        streamable_http_path=args.path,
    )


if __name__ == "__main__":
    main()
