# AGENTS.md — ML Programmer to ML Architect Aspire Journey

## Purpose
This workspace is for completing the **ML Programmer to ML Architect Aspire Journey on Percipio**. It serves as a learning/experimentation environment for ML architecture concepts. Each module (foundations → MLOps → architecture → specialization → capstone) is a self-contained project with its own `AGENTS.md`.

## Repository State
- Minimal setup: only Kilo config (`.kilo/kilo.jsonc`) and a directory marker (`.directory`)
- No code, dependencies, or build tooling yet — add per-project as you progress through the journey
- Each module warrants its own subdirectory/project with module-specific `AGENTS.md`

## Working in This Repo
- Treat as a scratchpad for journey exercises, notebooks, and prototype code
- Each module's `AGENTS.md` contains learning objectives, tools, and deliverables
- Do not copy guidance from module files into the root; reference them instead

## Kilo Configuration
- Config at `.kilo/kilo.jsonc` — LM Studio/OpenRouter providers with embedding models
- `model`: `openrouter/nvidia/nemotron-3.5-lightning:free` (primary)
- `subagent_model`: `lm_studio/nvidia/nemotron-3-nano-4b`
- `agent.compaction.model`: `lm_studio/nvidia/nemotron-3-nano-4b`
- `auto_complete_model`: `sweep-next-edit-1.5b`
- Small model: `lm_studio/qwen3.5-0_8b-tcg-ga`

## Agent Manager
- Use `agent_manager` to spawn worktrees for parallel module experiments
- Worktrees are git-isolated; use `mode: worktree` for branch-per-experiment
- Spawn local sessions with `mode: local` for same-directory tasks
- Each worktree gets its own Agent Manager card in the extension

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
2. Use `agent_manager` with `mode: worktree` to isolate experiment worktrees
3. Kilo will auto-select models from the config in `.kilo/kilo.jsonc`