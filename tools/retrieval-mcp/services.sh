#!/usr/bin/env bash
# Manage the local retrieval stack (rerank + retrieval MCP) in tmux.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/retrieval"
RERANK_BIN="${RERANK_BIN:-$HOME/.lmstudio/extensions/backends/llama.cpp-linux-x86_64-vulkan-avx2-2.67.0/llama-server}"
RERANK_MODEL="${RERANK_MODEL:-$HOME/.lmstudio/models/ggml-org/Qwen3-Reranker-0.6B-Q8_0-GGUF/qwen3-reranker-0.6b-q8_0.gguf}"
RERANK_DEVICE="${RERANK_DEVICE:-Vulkan0}"
RERANK_GPU_LAYERS="${RERANK_GPU_LAYERS:-99}"
RERANK_PORT="${RERANK_PORT:-1235}"
MCP_PORT="${MCP_PORT:-8765}"
MCP_SESSION="${MCP_SESSION:-retrieval-mcp}"
RERANK_SESSION="${RERANK_SESSION:-rerank}"

mkdir -p "$STATE_DIR"

usage() {
  cat <<EOF
Usage: $0 {start|stop|restart|status|logs}

  start    Start rerank and retrieval MCP in tmux sessions
  stop     Stop both tmux sessions
  restart  Stop, then start
  status   Show tmux sessions, ports, and health
  logs     Tail the service logs
EOF
}

require_tmux() {
  command -v tmux >/dev/null || {
    echo "tmux is required" >&2
    exit 1
  }
}

start_rerank() {
  if tmux has-session -t "$RERANK_SESSION" 2>/dev/null; then
    echo "rerank already running (tmux: $RERANK_SESSION)"
    return
  fi
  if [[ ! -x "$RERANK_BIN" ]]; then
    echo "rerank binary not found: $RERANK_BIN" >&2
    echo "Set RERANK_BIN to a llama-server build with --reranking support." >&2
    exit 1
  fi
  if [[ ! -f "$RERANK_MODEL" ]]; then
    echo "rerank model not found: $RERANK_MODEL" >&2
    exit 1
  fi
  tmux new-session -d -s "$RERANK_SESSION" -c "$HOME" \
    "exec '$RERANK_BIN' -m '$RERANK_MODEL' --reranking --pooling rank --host 127.0.0.1 --port '$RERANK_PORT' --ctx-size 4096 --device '$RERANK_DEVICE' -ngl '$RERANK_GPU_LAYERS' --threads 16 --parallel 4 --batch-size 2048 --ubatch-size 1024 > '$STATE_DIR/rerank.log' 2>&1"
  echo "started rerank on 127.0.0.1:$RERANK_PORT"
}

start_mcp() {
  if tmux has-session -t "$MCP_SESSION" 2>/dev/null; then
    echo "retrieval MCP already running (tmux: $MCP_SESSION)"
    return
  fi
  if [[ ! -x "$SCRIPT_DIR/.venv/bin/python" ]]; then
    echo "venv missing: $SCRIPT_DIR/.venv" >&2
    echo "Create it with: python3 -m venv --system-site-packages .venv && .venv/bin/pip install mcp" >&2
    exit 1
  fi
  tmux new-session -d -s "$MCP_SESSION" -c "$SCRIPT_DIR" \
    "exec .venv/bin/python retrieval_mcp.py --port '$MCP_PORT' > '$STATE_DIR/mcp.log' 2>&1"
  echo "started retrieval MCP on http://127.0.0.1:$MCP_PORT/mcp"
}

wait_for() {
  local url="$1" name="$2"
  for _ in $(seq 1 30); do
    if curl -s --max-time 2 "$url" >/dev/null 2>&1; then
      echo "$name ready"
      return 0
    fi
    sleep 1
  done
  echo "$name did not become ready; see $STATE_DIR" >&2
  return 1
}

case "${1:-}" in
  start)
    require_tmux
    if ! curl -sf --max-time 3 http://127.0.0.1:1234/v1/models >/dev/null 2>&1; then
      echo "warning: LM Studio is not responding on 127.0.0.1:1234" >&2
      echo "start it with: lms server start --port 1234" >&2
    fi
    start_rerank
    start_mcp
    sleep 2
    wait_for "http://127.0.0.1:$RERANK_PORT/health" "rerank" || true
    wait_for "http://127.0.0.1:$MCP_PORT/mcp" "retrieval MCP" || true
    ;;
  stop)
    require_tmux
    tmux kill-session -t "$MCP_SESSION" 2>/dev/null || true
    tmux kill-session -t "$RERANK_SESSION" 2>/dev/null || true
    echo "stopped retrieval services"
    ;;
  restart)
    "$0" stop
    "$0" start
    ;;
  status)
    require_tmux
    echo "tmux sessions:"
    tmux ls 2>/dev/null | grep -E "^($MCP_SESSION|$RERANK_SESSION):" || echo "  (none)"
    echo
    printf 'rerank  : '
    curl -s --max-time 3 "http://127.0.0.1:$RERANK_PORT/health" || echo "down"
    echo
    printf 'mcp     : '
    curl -s -o /dev/null -w '%{http_code}\n' --max-time 3 "http://127.0.0.1:$MCP_PORT/mcp" || echo "down"
    printf 'lmstudio: '
    curl -s -o /dev/null -w '%{http_code}\n' --max-time 3 http://127.0.0.1:1234/v1/models || echo "down"
    ;;
  logs)
    tail -n 40 "$STATE_DIR/rerank.log" "$STATE_DIR/mcp.log" 2>/dev/null || true
    ;;
  *)
    usage
    exit 1
    ;;
esac
