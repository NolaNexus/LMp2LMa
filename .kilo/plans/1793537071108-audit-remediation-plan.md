# Audit Remediation Plan (ATT-001..013) — verified state as of 2026-11-01 12:59

## Current state (re-verified this session; supersedes `.kilo/review_tickets.md` and memory)

| Ticket | Ticket says | Actually true now | Evidence |
|---|---|---|---|
| ATT-001 | 13 notebooks fail `json.load` | **All 32 notebooks parse** (`jq` OK, nbformat 4). The real problem now is that **code-cell sources hold literal `\"`**, so Python raises SyntaxError | `jq '.cells[1].source'` on `05_computational_theory` shows `sns.set_style(\"whitegrid\")`; a stray `"` line ends a cell at rendered line 272 |
| ATT-002 | Capstone 0% | 8 dirs, 5 ADRs (2–3 KB each, so not empty), plus `serving/domain.py` and `serving/llm/*_provider.py`, all **untracked**. No API, tests, infra, ops guide or retrospective | `ls capstone/**`, `git status` |
| ATT-003 | 05/06/11 are stubs | 05 (DDPM) and 06 (MoCo/MAE) are committed (db3e576). 11 has 34 cells | `git log`, `jq .cells|length` |
| ATT-005/011 | Grader and CI missing | Both exist (9f20037) but **cannot pass** (see Phase 2) | `.github/workflows/assessment.yml`, `tests/final_exam_grader.py` |
| ATT-007 | Lock file malformed | Still malformed: one line with literal `\n` | `requirements-lock.txt:1` |
| ATT-008 | Devcontainer minimal | Still minimal | `.devcontainer/devcontainer.json` |

Code cells containing literal `\"` (count per notebook):
- **T1:** 05_computational_theory ×9, 06_bayesian ×4, 07_rl ×5
- **T2:** 04_transformers ×1, 10_recommender ×7
- **T3:** 02_feature_store ×7, 03_mlflow ×1, 06_drift ×1
- **T4:** 02_triton ×2, 03_quantization ×5, 05_cost ×6, 06_fm_finetune ×5

No committed notebook has stored outputs.

Uncommitted work and debris in the tree:
- 5 notebooks modified with near-symmetric diffs. These look like rebuild-script rewrites.
- 8 `*.ipynb.bak` files. These are pre-fix copies that still fail to parse.
- 8 `.kilo/{fix,rebuild}_notebooks*.py` scripts.
- A root file named `=1.5.1`, left behind by a shell redirect.
- `test.html` (3.8 MB).
- `artifacts/adult_income_pipeline.joblib` (108 MB).
- `data/` datasets.
- `.kilo/kilo.jsonc` edits and companion-smoke deletions. These are user config and out of scope, so leave them alone.

## Decisions
- Treat the repo as the source of truth. The ticket file is stale, so it gets rewritten in Phase 0.
- Use a deterministic repair script and validate every code cell with `ast.parse`. Strip IPython magics/`!` lines before validating. Don't edit by hand except where the script can't fix a cell.
- Large binaries and datasets don't get committed. Add them to `.gitignore`.
- One commit per phase, referencing ticket IDs.

## Phase 0 — Hygiene and baseline
1. Review `git diff` for the 5 modified notebooks. Compare normalized sources:
   ```
   jq '[.cells[]|{cell_type,s:(.source|if type=="array" then join("") else . end)}]'
   ```
   compared against `HEAD`. If only the formatting changed, keep the files. If content was lost, `git restore` them.
2. Delete:
   - `*.ipynb.bak`
   - `=1.5.1`
   - `test.html`
   - `tests/__pycache__`
   - `.kilo/{fix,rebuild}_notebooks*.py` (the old versions remain in git history and transcripts)
3. Create a `.gitignore` covering:
   - `artifacts/*.joblib`
   - `data/`
   - `track-*/data/`
   - `__pycache__/`
   - `.pytest_cache/`
   - `.venv/`
   - `mlruns/`
   - `*.bak`
4. Add `tools/validate_notebooks.py`. It does three things:
   - runs `json.load` and `nbformat.validate` on every notebook;
   - runs `ast.parse` on every code cell, after removing magic and `!` lines;
   - exits non-zero and reports `file:cell_index:lineno` for each failure.

   This becomes the gate for Phase 1.

## Phase 1 — ATT-001: repair code-cell corruption
1. Add `tools/fix_escaped_sources.py`. For each code cell that fails `ast.parse`, it:
   - replaces `\"` with `"` and `\\n` with `\n` where needed;
   - drops a lone trailing `"` line;
   - re-runs `ast.parse` and writes the cell only if it now parses;
   - logs any cell that still fails.

   Write with `nbformat.write` so the JSON stays canonical.
2. Fix the remaining logged cells by hand (expected cases: string literals that legitimately contained `\"`).
3. Check that each notebook's markdown cells contain no literal `\"`, and fix any found the same way.
4. Gate:
   - `tools/validate_notebooks.py` reports 0 failures on all 32 notebooks.
   - For each of the 12 affected notebooks, `git diff` shows only quote/newline changes.

## Phase 2 — ATT-005/011: make assessment actually run
1. Move `tests/test_notebooks.py` from its `pass` placeholder to real checks: parametrize over the notebooks and call the validator logic (parse plus AST). Mark execution tests `slow`.
2. `final_exam_grader.py`:
   - Guard non-string `expected` (`str(expected)`). The current `.lower()` crashes on numbers.
   - Make `concept` matching require ≥50% of the keywords, not any single one.
   - Return status `NOT_EXECUTED` when the notebook has no outputs.
   - Add `nbformat` to `requirements-assessment.txt`.
3. Add `tests/test_grader.py`. Use a tiny fixture notebook with known outputs and check pass, fail and missing-output cases.
4. `assessment.yml`:
   - Install from `requirements-ci.txt` + `requirements-assessment.txt`. Get CPU torch via `--extra-index-url`, not `--index-url`: the current line makes pip look up pytest and nbval on the PyTorch index.
   - Add `pytest-timeout`, or drop `--timeout`.
   - Run the validator.
   - Execute the fast-subset notebooks with `jupyter nbconvert --execute --to notebook --output-dir executed/`. Point the grader at `executed/` through a `--notebook-dir` argument.
   - Remove `require('glob')` from the github-script step and use `fs.readdirSync` instead.
5. Gate, run locally with `conda activate ml-arch`:
   - `pytest tests -m "not slow"` passes.
   - `pytest --nbval-lax` passes on the 4 fast-subset notebooks.
   - The grader produces JSON for all 4 tracks.

## Phase 3 — Execution sweep (prerequisite for content work)
1. Execute every notebook in the `ml-arch` env, with a timeout per notebook. Record pass/fail and the first error in `.kilo/execution_report.md`.
2. Classify each failure:
   - missing dependency → add it to the requirements;
   - dataset download / network;
   - deprecated API (e.g. `torchtext` in 03_rnn_seq, which is deprecated since torch 2.4);
   - real bug.
3. Fix the dependency and API failures. Where a notebook would download a dataset or need a GPU, add a small offline fallback (synthetic or sklearn data) behind a `QUICK_MODE` flag so CI can run it.
4. Gate: every notebook either executes in `QUICK_MODE` or is explicitly listed as GPU-only in `tests/conftest.py`, with the reason.

## Phase 4 — Content gaps (ATT-006, ATT-010, ATT-004)
Each notebook below must pass Phase 3's gate before it counts as done.
1. ATT-006: 01–04 Track 2. Real training loop, held-out metrics and MLflow logging, on small datasets that work in `QUICK_MODE`.
2. ATT-010:
   - 08_gnn: add a second task, either link prediction or graph classification on a small TU dataset.
   - 07_nlp_finetune: replace the synthetic data with a small Hugging Face dataset slice, e.g. `databricks-dolly-15k` (~200 rows), and add eval metrics.
3. ATT-004: new Track 4 notebooks `07_system_design`, `08_data_architecture`, `09_platform_engineering`, `10_serving_architecture`, `11_iac`, `12_profiling`. Each has runnable code: a requirements→capacity calculator, a lambda/kappa sim, a batching/caching benchmark, Terraform/Helm templates validated with `terraform validate`/`helm lint` when the tools are present, and `torch.profiler`.
4. Add a checkpoint entry to `checkpoints/track_04_ml_architect.json` for each new notebook, and raise the Track 4 minimum in `test_notebook_count` to 12.

## Phase 5 — ATT-002: Capstone (Theme 5, LLM customer support)
1. Review the untracked `capstone/serving/**` and `docs/adr-*.md`. Check that the ADRs have Context, Decision, Consequences and Alternatives, then commit them.
2. Add `capstone/serving/api/app.py` (FastAPI `/chat`, `/health`), using `mock_provider` by default so it runs offline.
3. Add a RAG/retrieval layer over a small FAQ corpus in `capstone/data/raw/`.
4. Add `monitoring/` (latency/token metrics plus a drift check on query embeddings) and `governance/` (model card, PII redaction).
5. Add `capstone/tests/`, a pytest suite that uses the mock provider. Hook it into CI.
6. Add `infrastructure/`: a Dockerfile, a Helm chart skeleton (`helm lint`) and Terraform (`terraform validate`).
7. Write `docs/architecture.md`, `docs/operations.md` (runbooks) and `docs/retrospective.md`.

## Phase 6 — DevOps polish (ATT-007, 008, 009, 012, 013)
1. ATT-007: regenerate `requirements-lock.txt` from `pip-compile requirements.txt`, and produce `requirements-{gpu,ci,assessment}.lock` the same way. CI installs from the locks.
2. ATT-008: `devcontainer.json` gets:
   - the python and docker-in-docker features;
   - `forwardPorts` 8501/8888;
   - a `postStartCommand` that runs `tools/validate_notebooks.py`;
   - GPU `runArgs` made optional, because they break Codespaces.
3. ATT-009: `streamlit run dashboard/app.py --server.headless true` starts. Check it with a smoke test using `streamlit.testing.v1.AppTest` in `tests/test_dashboard.py`.
4. ATT-012: `pyproject.toml` with ruff (lint + format; skip black, since ruff format replaces it) and `.pre-commit-config.yaml` with ruff and `nbstripout`.
5. ATT-013: get the owner/repo from `git remote -v`. Replace `YOUR_USER` in the README and BADGES, and insert a Colab badge markdown cell at the top of each notebook (scripted).

## Phase 7 — Close-out
- Rewrite `.kilo/review_tickets.md` with a status per ticket and the verifying command output.
- Update project memory. Correct the stale "13 JSON parse errors" fact: the remaining issue was source escaping, and it was fixed in Phase 1.

## Risks
- **Unescaping can break legitimate `\"` inside strings.** Mitigation: per-cell `ast.parse` gate and manual review of the logged cells.
- **The 5 modified notebooks may contain regressions from the rebuild scripts.** Mitigation: the Phase 0 normalized diff.
- **Dataset and GPU dependencies make CI flaky.** Mitigation: `QUICK_MODE` and an explicit GPU-only list.
- **Running `python` from the agent's bash is blocked by the current permission rules.** Whoever implements needs those permissions (or the user runs the commands).

## Validation summary
1. `python tools/validate_notebooks.py` → 0 failures.
2. `pytest tests capstone/tests -m "not slow"` → green.
3. The Phase 3 execution report shows all notebooks pass or are justified as GPU-only.
4. The CI workflow is green on a PR.
5. The dashboard AppTest passes.
