#!/usr/bin/env bash
# Lint the OpenCode skills in .opencode/skills.
#
#   tools/skills-lint.sh                 # lint, human output
#   tools/skills-lint.sh --json          # machine-readable
#   tools/skills-lint.sh --no-embed      # skip the description-overlap check
#   tools/skills-lint.sh --skills-dir /tmp/x   # lint a scratch tree
#
# Exits 1 when any error is reported. Warnings never fail the build.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Prefer the retrieval MCP venv (it has the same stdlib-only needs and is known
# to be 3.12), then the ambient interpreter.
PYTHON="${SKILLS_LINT_PYTHON:-}"
if [[ -z "$PYTHON" ]]; then
  if [[ -x "$SCRIPT_DIR/retrieval-mcp/.venv/bin/python" ]]; then
    PYTHON="$SCRIPT_DIR/retrieval-mcp/.venv/bin/python"
  else
    PYTHON="$(command -v python3)"
  fi
fi

exec "$PYTHON" "$SCRIPT_DIR/skills_lint.py" "$@"
