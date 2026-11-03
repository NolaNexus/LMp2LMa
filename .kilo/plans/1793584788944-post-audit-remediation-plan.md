# Post-Audit Remediation Plan v2 — aligned to the 2026-11-02 audit

**Supersedes** `.kilo/plans/1793537071108-audit-remediation-plan.md`. That plan's Phases 0–2 and 4–5 are verified complete: all 38 notebooks pass `tools/validate_notebooks.py`; pytest shows 102 passed / 2 deselected; capstone, ADRs, checkpoints, locks, and devcontainer all exist and are valid. This plan carries forward only what the new audit found.

**Verified environment facts**: tests must run from `base` (miniconda) or `anaconda3/envs/ml-arch` — `ml-arch` is NOT visible via miniconda's conda (audit gap G9; activate via `/home/nola/anaconda3/envs/ml-arch` when needed). Repo has 0 remotes. Working tree has 2 modified tracked files.

## Findings carried forward (from the audit)

Gaps: G1 no git remote; G2 `.venv` tracked (1,771 files); G3 `YOUR_USER` placeholders (`README.md:22-23`, `BADGES.md`); G4 badges documented but applied to 0/38 notebooks; G5 empty `capstone/training/` + `capstone/serving/plugins/` scaffolding documented in `capstone/README.md:12`; G6 execution blockers (torchtext in `track-02-dl-programmer/03_rnn_seq.ipynb`; 4 notebooks with network `download=True`; only 4 honor `QUICK_MODE`); G7 pre-commit/pip-compile installed nowhere; G8 uncommitted `.kilo/review_tickets.md` + `artifacts/pipeline_metadata.json`; G9 conda env mismatch.

Redundancies: (A) tracked-but-ignored artifacts; (B) data/report duplication; (C) config drift (two dev Dockerfiles, re-pinned requirements); (D) obsolete one-off repair tools; (E) stale docs and worktree copies; (F) shell-accident `=` files.

## Required user inputs (not resolvable in-repo)
1. **Remote URL** for `git remote add origin <url>` (G1). Needed before Phase 1 step 5 and Phase 5 badges.
2. **Worktree deletion consent** — `.kilo/worktrees/{charming-cast,held-giraffe}` are agent-manager cards containing stale pre-repair notebooks. Default: **leave untouched** (project constraint: never edit worktree copies); delete only if user confirms they are abandoned.
3. **AUDIT_REPORT.md disposition** — recommendation: replace the stale report with a regenerated current-state version in Phase 6.

## Phase 1 — VCS hygiene, dedup, remote (G1, G2, G8; redundancies A, B, F)
1. Untrack ignored-before-tracked artifacts (do NOT rewrite history — filter-repo is destructive and out of scope):
   ```
   git rm -r --cached .venv
   git rm -r --cached track-03-ml-engineer/mlruns
   git rm --cached data/cifar-10-python.tar.gz
   ```
2. Fix `.gitignore` patterns so nested paths actually match: change `mlruns/` → `**/mlruns/`. `data/`, `.venv/`, `=*` already cover the remaining paths once untracked.
3. Delete from disk (untracked duplicates/accidents): `track-02-dl-programmer/data/cifar-10-python.tar.gz` (2 MB truncated twin of the 22.6 MB root archive; notebooks must read only the root `data/` copy or download), `track-02-dl-programmer/=0.41.0`, `analysis_output.txt`. Leave `.kilo/worktrees/=1.5.1` files alone (input #2).
4. Commit the two modified files (`git add .kilo/review_tickets.md artifacts/pipeline_metadata.json`) — the ticket rewrite reflects verified state; one commit: `chore: untrack venv/data/mlruns, sync ticket ledger`.
5. Add the remote from input #1 and `git push -u origin master`.
   Gate: `git ls-files | grep -cE "^\.venv/|mlruns/|tar\.gz"` → 0; `git status` clean; push succeeds.

## Phase 2 — Consolidate divergent dev images (redundancy C)
1. Make `.devcontainer/Dockerfile` the single dev-image source (python 3.12-slim, multi-stage dev/gpu-dev). Update `docker-compose.yml` services to `build.dockerfile: .devcontainer/Dockerfile`, retargeting `cpu-dev`→`dev`, keep `gpu-dev`, and point the `dashboard` service at `dev`.
2. Delete the root `Dockerfile` (it duplicates dev-image intent with a drifted python 3.10/CUDA 12.1 toolchain and different requirements). `capstone/infrastructure/Dockerfile` is a distinct production image — keep.
3. Gate: `docker compose build dev` succeeds (or document Docker-unavailable fallback); `devcontainer.json` still builds; only one dev Dockerfile remains.

## Phase 3 — Dead tooling and stale docs (G3 partially, redundancies D, E)
1. `git rm` obsolete one-off repair scripts (all 38 notebooks validate; history preserves them): `tools/fix_escaped_sources.py`, `tools/recover_from_original.py`, `tools/repair_cells.py`, `tools/generate_track04_notebooks.py`. Keep `validate_notebooks.py`, `execution_sweep.py`, `add_notebook_badges.py`, `normalize_notebooks.py` (normalize is still referenced for output-free convention).
2. Replace stale `AUDIT_REPORT.md` with a regenerated current-state audit (per input #3 recommendation) or delete it and point readers at `.kilo/review_tickets.md`.
3. Fix `BADGES.md`: drop the "Create `.devcontainer/devcontainer.json`" section (it exists); keep badge snippets.

## Phase 4 — Notebook execution blockers (G6)
1. `track-02-dl-programmer/03_rnn_seq.ipynb`: remove the `torchtext` import/usage; replace dataset/vocab usage with torch-native equivalents (list-built vocab + `nn.Embedding`/`nn.GRU` already present) and an offline synthetic fallback.
2. The 4 `download=True` notebooks: add small offline fallbacks (synthetic or bundled sklearn data) behind `QUICK_MODE`, per the repo convention of executing to `/tmp/executed` without mutating source notebooks.
3. Extend `QUICK_MODE` support from 4 to at least the CI fast subset plus any notebook the sweep flags as network-bound. Preserve the repo rule: notebooks stay output-free (0 stored outputs).
   Gate: `QUICK_MODE=1 python tools/execution_sweep.py --quick --timeout 600` improves strictly vs the prior report (only explicitly justified GPU-only failures remain, listed in `tests/conftest.py` with reasons).

## Phase 5 — Capstone scaffold (G5)
1. Implement minimal real code in `capstone/training/`: `train.py` (small fine-tune loop over a toy corpus with MLflow logging, mock/offline LLM provider reuse) + `configs/` — enough to honor `capstone/README.md:12` and the retraining trigger in `capstone/README.md:69`. Add a pytest in `capstone/tests/`.
2. `capstone/serving/plugins/`: either add a real plugin example (registered provider entry point) or remove the empty dir and its README mention. Recommendation: add one minimal plugin to justify the extension point.
3. Gate: `pytest capstone/tests -m "not slow"` stays green; `pip install -e .` imports the new modules.

## Phase 6 — Badges, placeholders, DevOps polish (G3, G4, G7)
1. After Phase 1 step 5 (remote exists): replace `YOUR_USER` with the real owner/repo in `README.md:22-23` and `BADGES.md`.
2. Run `tools/add_notebook_badges.py` across all 38 notebooks (markdown cells only, nbformat-written, output-free) and re-run `tools/validate_notebooks.py`.
3. Install tooling: `pip install pre-commit pip-tools`; `pre-commit install`; verify hooks run (`pre-commit run --all-files`); regenerate any drifted lock with `pip-compile` so locks stay the CI source of truth.
   Gate: 38/38 notebooks contain a badge cell; grep finds no `YOUR_USER`; `pre-commit run --all-files` passes.

## Phase 7 — Close-out
1. Final validation:
   - `python3 tools/validate_notebooks.py` → all valid.
   - `python -m pytest tests capstone/tests -m "not slow"` → green.
   - `git ls-files` contains no `.venv/`, `mlruns/`, or `*.tar.gz` entries.
   - `git status` clean; branch pushed.
2. Rewrite `.kilo/review_tickets.md` statuses against this plan's phases with verifying commands.
3. Save memory corrections: ADRs/checkpoints/locks/devcontainer gaps are RESOLVED; `.venv`+mlruns+tarball untracked; remote configured; remaining execution blockers are torchtext and QUICK_MODE coverage.

## Risks
- **Untracking large files does not shrink history** — the `.venv` blobs stay in past commits; a fresh clone is still heavy until history is rewritten (explicitly out of scope unless the user requests it before the first push).
- **Badges depend on the remote URL** — Phase 6 step 1 is blocked without input #1; do it after push, not before.
- **docker-compose consolidation may break local GPU workflows** that rely on the old root image; mitigation: keep the `gpu-dev` target semantics in the consolidated Dockerfile.
- **QUICK_MODE fallbacks must not mutate notebooks** — keep outputs stripped (repo constraint), execute to `/tmp/executed`.

## Out of scope
- Git history rewriting (filter-repo).
- `.kilo/worktrees/**` content changes (stale copies; agent-manager-managed).
- `.kilo/kilo.jsonc` and user config.
- Full capstone production hardening beyond the minimal training scaffold.
