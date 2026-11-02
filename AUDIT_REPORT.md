# Repository Audit Report — verified state as of 2026-11-02

**Repository**: https://github.com/NolaNexus/LMp2LMa (master, pushed)
**Supersedes**: the 2026-11-01 edition, whose claims of capstone 0%, template-only track-02
notebooks, and broken checkpoints were all stale.

## Verified current state

| Area | Status | Evidence |
|---|---|---|
| Notebook structural validity | ✅ 38/38 valid (JSON + nbformat + ast) | `python3 tools/validate_notebooks.py` |
| Unit / assessment suite | ✅ 102 passed, 2 deselected | `QUICK_MODE=1 python -m pytest tests capstone/tests -m "not slow"` |
| Checkpoint JSONs (4 tracks) | ✅ All parse | `json.load` on `checkpoints/*.json` |
| Capstone | ✅ Implemented and committed: FastAPI serving, LLM provider abstraction, RAG, monitoring, governance, tests, Helm + Terraform | `capstone/**`, commit `30a98b2` |
| ADRs | ✅ adr-001..005 written (1.9–3.0 KB each) | `capstone/docs/` |
| Assessment CI | ✅ `.github/workflows/assessment.yml` with nbval fast subset | CI file |
| Locks | ✅ `requirements-{ci,assessment,gpu-cu126}.lock` + `requirements-lock.txt` | repo root |
| Remote / push | ✅ origin `git@github.com:NolaNexus/LMp2LMa.git`, master pushed 2026-11-02 | `git remote -v` |

## Notebook inventory (38)

- track-01-ml-programmer: 7 · track-02-dl-programmer: 11 · track-03-ml-engineer: 8 · track-04-ml-architect: 12
- Repo convention holds: 0 stored outputs in committed notebooks.

## Gaps resolved by the 2026-11-02 remediation (commits `274fd13`, `591e259`)

- **Tracked `.venv`** (1,771 files), **`track-03-ml-engineer/mlruns`** (82 files), and the
  22.6 MB CIFAR tarball removed from the index; `.gitignore` now uses `**/mlruns/`.
- **No git remote** → configured and pushed.
- **Dev Dockerfile drift** → root `Dockerfile` deleted; `docker-compose.yml` builds from
  `.devcontainer/Dockerfile` (single dev/gpu-dev source); gpu stage uses
  `requirements-gpu-cu126.txt` (Quadro M5000 / sm_52).
- **Obsolete one-off repair scripts** (`fix_escaped_sources`, `recover_from_original`,
  `repair_cells`, `generate_track04_notebooks`) deleted; durable tooling kept.
- Stale worktree copies `.kilo/worktrees/{charming-cast,held-giraffe}` deleted (user-approved).
- `BADGES.md` devcontainer section removed (it described an already-existing config).

## Remaining known gaps (tracked in `.kilo/plans/1793584788944-post-audit-remediation-plan.md`)

1. **Execution blockers**: `torchtext` import in `track-02-dl-programmer/03_rnn_seq.ipynb`
   (torchtext is discontinued); 4 notebooks rely on network `download=True`; only 4 of 38
   honor `QUICK_MODE`.
2. **Badge application**: `tools/add_notebook_badges.py` exists but badges not yet applied
   to the 38 notebooks; `README.md` Colab/Codespaces badges still carry `YOUR_USER`.
3. **Capstone scaffolding**: `capstone/training/` documented in `capstone/README.md:12` but
   empty; `capstone/serving/plugins/` empty.
4. **Tooling not installed**: `pre-commit` / `pip-compile` absent from the environment
   although `.pre-commit-config.yaml` and lock files are committed.

## Method note

All statuses above were re-verified with commands, not carried over from memory or the
2026-11-01 report.
