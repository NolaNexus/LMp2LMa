#!/usr/bin/env bash
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PYTHON_BIN="${JUPYTER_MCP_PYTHON:-/home/nola/anaconda3/envs/ml-arch/bin/python}"
MCP_PORT="${JUPYTER_MCP_PORT:-3002}"
SERVER_PORT="${JUPYTER_SERVER_PORT:-8899}"
LOG="${JUPYTER_MCP_LOG:-/tmp/jupyter-mcp-server.log}"

mcp_up() {
  curl -s -o /dev/null -m 2 "http://127.0.0.1:${MCP_PORT}/mcp"
}

if ! mcp_up; then
  mkdir -p "$(dirname "${LOG}")"
  nohup "${PYTHON_BIN}" -m jupyterlab.labapp \
    --no-browser \
    --ServerApp.ip=127.0.0.1 \
    --ServerApp.port="${SERVER_PORT}" \
    --ServerApp.port_retries=0 \
    --ServerApp.open_browser=False \
    --ServerApp.token="" \
    --ServerApp.root_dir="${REPO_ROOT}" \
    --config="${REPO_ROOT}/.jupyter/jupyter_server_config.py" \
    >"${LOG}" 2>&1 &

  for _ in $(seq 1 60); do
    if mcp_up; then
      break
    fi
    sleep 1
  done
fi

if ! mcp_up; then
  echo "jupyter-mcp: MCP endpoint on port ${MCP_PORT} did not come up; see ${LOG}" >&2
  exit 1
fi

exec "${PYTHON_BIN}" -m jupyter_server_mcp.proxy --cwd "${REPO_ROOT}"
