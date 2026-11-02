# AGENTS.md — ML Programmer to ML Architect Aspire Journey

## Purpose
This workspace is for completing the **ML Programmer to ML Architect Aspire Journey on Percipio**. It serves as a learning/experimentation environment for ML architecture concepts. Each module (foundations → MLOps → architecture → specialization → capstone) is a self-contained project with its own `AGENTS.md`.

## Repository State
- Tracks `track-01-ml-programmer` … `track-04-ml-architect` plus `capstone/`, all notebook-driven
- Tooling in `tools/`: notebook validation and normalization, execution sweep, the local retrieval MCP
- Agent skills in `.opencode/skills/`; decisions in `docs/adr/`
- Retrieval stack (embed + rerank + MCP) managed by `tools/retrieval-mcp/services.sh`
- Plans live outside the repo in `~/.opencode/plan/`

## Working in This Repo
- Treat as a scratchpad for journey exercises, notebooks, and prototype code
- Each module's `AGENTS.md` contains learning objectives, tools, and deliverables
- Do not copy guidance from module files into the root; reference them instead

## OpenCode Configuration
- Global config at `~/.config/opencode/opencode.jsonc` — model routing, agent models, retrieval MCP
- Agents (`docsmith`, `reviewer`, `scout`, `worker`) at `~/.config/opencode/agents/`
- Retrieval MCP wired as a remote server at `http://127.0.0.1:8765/mcp`
- No project-level config file; this repo relies on the global one

## Model Routing & Handoff

Delegation is the default. The orchestrator plans and hands scoped work to a subagent; it does not implement large changes inline.

| Role | Model | Notes |
|------|-------|-------|
| Orchestrator / parent | `openrouter/deepseek/deepseek-v4.1-flash-1017#high` | 1M context. Plans, decomposes, integrates. |
| Worker | `openrouter/deepseek/deepseek-v4.1-flash-1017#high` | Scoped edits + tests. No further delegation. |
| Scout | `openrouter/upstage/solar-mini4` | Read-only search and summarization. |
| Reviewer | `openrouter/anthropic/claude-haiku-5.5` | Read-only diff review. |
| Docsmith | `openrouter/upstage/solar-mini4` | Markdown only. |
| Compaction | `openrouter/deepseek/deepseek-v4.1-flash-1017#low` | Context must be >= the parent's. |

- Max spawn depth is **1**. Children do not spawn grandchildren.
- Cap concurrent children at **6** and keep iterations bounded (120 for Hermes delegation).
- If a child is blocked twice on the same issue, stop and escalate to the user instead of retrying or spawning deeper.
- Prefer handing off: file discovery, broad greps, test runs, doc updates, and isolated edits.
- Keep implementation in the parent only for small, single-file changes.
- Retrieval is served by the local MCP at `http://127.0.0.1:8765/mcp` (`search`, `fetch`, `reindex`, `stats`). Use `search` before broad grep when looking for concepts across notebooks.
- Services run in tmux: `tools/retrieval-mcp/services.sh {start|stop|status|logs}`. Rerank is on `:1235`, embeddings on LM Studio `:1234`.
- Zed external agents (OpenCode, Hermes) use ACP and their own auth. The native Zed agent needs its own OpenRouter key in the keychain; it does not read Hermes' `.env`.

## Worktrees
- Isolate parallel experiments in git worktrees (`tools.opencode.worktree_create`), one branch per experiment
- Sessions can be moved between checkouts without losing context (`session_move`)
- Worktrees share the repo's `.opencode/skills`; a skill edit is visible everywhere after `/reload`

## Suggested Structure (as you grow)
```
LMp2LMa/
├ module-01-foundations/
├ module-02-mlops/
├ module-03-architecture/
├ module-04-specialization/
└ capstone/
```
Add project-specific `AGENTS.md` or `README.md` in each subdirectory as they materialize.

## Getting Started
1. Read the module `AGENTS.md` for your target module before starting
2. Use an OpenCode worktree to isolate experiment branches
3. OpenCode selects models from `~/.config/opencode/opencode.jsonc`

## Skills

Agent skills live in `.opencode/skills/<id>/SKILL.md`; retired ones move to
`.opencode/skills/.archive/`. The leading dot is load-bearing — the loader skips
hidden directories, so an underscore-prefixed archive would load as live skills.

- Active skills: `repo-orientation`, `notebook-editing`, `retrieval-mcp`, `authoring-skills`.
  Read `authoring-skills` before writing or revising one.
- `tools/skills-lint.sh` lints them: frontmatter, ID pattern, `status`/location
  consistency, dead path and command references, description overlap, git staleness.
  It is the **only** enforcement of lifecycle state — the loader ignores custom
  frontmatter keys, so `status: archived` alone retires nothing.
- Decisions: `docs/adr/ADR-001` (format and location), `ADR-002` (telemetry),
  `ADR-003` (lifecycle). Read ADR-001 before adding a skill.
- Tests: `python3 -m pytest tests/test_skills_lint.py -q`.
- Telemetry: `tools/skills_telemetry.py` reads `~/.local/share/opencode/opencode.db`
  read-only and reports which skills fired and a **proxy** outcome. It is not
  ground truth; labelled outcomes come from the golden task set.
