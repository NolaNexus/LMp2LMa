# Repository Audit Tickets
**Generated**: 2026-11-01  
**Scope**: Full repository audit against Skillsoft ML Programmer → ML Architect Aspire Journey  
**Evidence Standard**: Line/file/cmd-output references, not summaries  

---

## ATT-001: 13 Notebooks Have JSON Parse Errors (Blocking Execution)

**Severity**: CRITICAL  
**Category**: Notebook Integrity  
**Evidence**: `python3 -c "import json; json.load(open(f))"` fails on 13/32 notebooks with `JSONDecodeError` at lines 45-476  

**Broken Notebooks**:
| Track | Notebook | Error | Line |
|-------|----------|-------|------|
| track-01 | 05_computational_theory.ipynb | Expecting value | 251 |
| track-01 | 06_bayesian_methods.ipynb | Expecting value | 78 |
| track-01 | 07_reinforcement_learning.ipynb | Expecting value | 141 |
| track-02 | 03_rnn_seq.ipynb | Expecting ',' delimiter | 291 |
| track-02 | 04_transformers.ipynb | Expecting value | 165 |
| track-02 | 09_time_series.ipynb | Expecting ',' delimiter | 318 |
| track-02 | 10_recommender_systems.ipynb | Expecting ',' delimiter | 476 |
| track-03 | 02_feature_store.ipynb | Expecting value | 343 |
| track-03 | 03_mlflow_advanced.ipynb | Expecting value | 210 |
| track-04 | 02_triton_serving.ipynb | Expecting ',' delimiter | 88 |
| track-04 | 03_quantization.ipynb | Expecting ',' delimiter | 48 |
| track-04 | 05_cost_optimization.ipynb | Expecting value | 45 |
| track-04 | 06_foundation_model_finetune.ipynb | Expecting value | 77 |

**Acceptance Criteria**: All 32 notebooks pass `json.load()` and `pytest --nbval` execution  
**Notes**: Original files preserved at git commits e67a212, ff74382, 12e2e94, ee6d36d per prior session. Manual array-boundary edits required (quote/comma/close fixes).

---

## ATT-002: Capstone Implementation Entirely Missing (0% Complete)

**Severity**: CRITICAL  
**Category**: Capstone Integration  
**Evidence**: `ls -la /home/nola/LMp2LMa/capstone/` shows only `AGENTS.md` (1.7KB) and `README.md` (7.9KB) — no subdirectories, no ADRs, no working system  

**Missing Deliverables** (per capstone/README.md):
- Architecture Document (20%)
- ADRs — 5+ entries (25%) — **zero ADR files exist**
- Working System (30%) — no code, no deployment
- Operations Guide (15%) — no runbooks
- Retrospective (10%) — no document
- Project Structure — 8 subdirectories (data/, training/, serving/, infrastructure/, monitoring/, docs/, governance/, tests/) all missing

**Acceptance Criteria**: 
- Capstone directory structure created with all 8 subdirectories
- 5+ ADR files in `capstone/docs/` with proper format (Title, Status, Context, Decision, Consequences, Alternatives)
- Working end-to-end system for one chosen theme (Theme 5 LLM-powered Customer Support recommended)
- Operations guide and retrospective documents

---

## ATT-003: Track 2 (DL Programmer) — 3 Specialization Tracks Non-Functional

**Severity**: CRITICAL  
**Category**: Curriculum Coverage  
**Evidence**: Direct inspection of notebooks  

| Notebook | Status | Skillsoft Courses Affected |
|----------|--------|---------------------------|
| `06_self_supervised.ipynb` | **Template only** — MoCo/MAE are text overviews, no executable training | Self-Supervised Learning (44m) |
| `11_science_healthcare.ipynb` | **STUB ONLY** — 5 lines, no executable content | Science/Healthcare (2 courses, ~1h20m) |
| `05_generative.ipynb` | Diffusion = concept only, no training loop | Diffusion (38m) |

**Acceptance Criteria**:
- `06_self_supervised.ipynb`: Executable MoCo v2/v3 + MAE training on CIFAR-10/ImageNet subset with linear probe evaluation
- `11_science_healthcare.ipynb`: Full implementation — uncertainty quantification (calibration curves, conformal prediction), domain adaptation (Hospital A→B shift simulation), clinical trial simulation
- `05_generative.ipynb`: Minimal DDPM/latent diffusion training loop added

---

## ATT-004: Track 4 (ML Architect) — 6 of 12 Skillsoft Courses Not Addressed (50% Gap)

**Severity**: HIGH  
**Category**: Curriculum Coverage  
**Evidence**: Audit cross-reference against Skillsoft journey curriculum  

**Missing Courses**:
1. System Design / Requirements Gathering
2. Data Architecture (Lakehouse, Streaming, Kappa/Lambda)
3. Platform Engineering (Internal ML Platforms, Self-serve Infrastructure)
4. Serving Architecture deep-dive (batching, caching, model composition)
5. Infrastructure as Code (Terraform, Helm, ArgoCD)
6. Profiling (Nsight, PyTorch Profiler, TensorBoard)

**Acceptance Criteria**: 6 new notebooks or major sections added covering these topics with executable content

---

## ATT-005: Assessment Infrastructure Not Functional (Scaffolded Only)

**Severity**: HIGH  
**Category**: Assessment Infrastructure  
**Evidence**: 
- `tests/final_exam_grader.py` line 6: returns `"status": "READY"` without grading logic
- `pytest --nbval` never executed (no CI run verified)
- Checkpoint questions not linked to notebook outputs (no auto-grading)
- No GitHub Actions workflow for automated assessment

**Files**:
- `tests/test_notebooks.py` — parametrized but untested
- `tests/run_assessment.py` — orchestrates but unrun
- `checkpoints/*.json` — well-structured but questions expect specific values with no extraction logic

**Acceptance Criteria**:
- `pytest --nbval` passes on all 32 notebooks
- Auto-grading logic connects checkpoint questions to notebook cell outputs
- Final exam grader scores answers against expected values
- GitHub Actions workflow runs assessment on PR

---

## ATT-006: Track 2 Core Notebooks Need Quality Review (4 Notebooks)

**Severity**: HIGH  
**Category**: Notebook Quality  
**Evidence**: Audit notes template-level content in:
- `01_nn_fundamentals.ipynb` — needs real training, real metrics
- `02_cnn_vision.ipynb` — needs real training, real metrics  
- `03_rnn_seq.ipynb` — broken JSON (ATT-001) + template content
- `04_transformers.ipynb` — broken JSON (ATT-001) + template content

**Acceptance Criteria**: All 4 notebooks have real training loops, real evaluation metrics, proper experiment tracking

---

## ATT-007: No Lock Files for Reproducibility (requirements-gpu.lock missing)

**Severity**: MEDIUM  
**Category**: DevOps/Reproducibility  
**Evidence**: 
- `requirements-lock.txt` exists but is single-line with escaped `\n` (186 bytes), not proper lock format
- `requirements-gpu.lock` does not exist
- `requirements-ci.lock`, `requirements-assessment.lock` do not exist

**Acceptance Criteria**: 
- `pip-tools` or `pip freeze` generates proper lock files for all 4 requirement sets
- Lock files committed and CI uses them for reproducible installs

---

## ATT-008: .devcontainer Minimal — Codespaces Not Fully Functional

**Severity**: MEDIUM  
**Category**: DevOps/Environment  
**Evidence**: `.devcontainer/devcontainer.json` (346 bytes, 8 lines) — no `features`, no `mounts`, no `forwardPorts`, no `postStartCommand` for environment validation

**Acceptance Criteria**: 
- Full devcontainer.json with features (python, docker-in-docker), port forwarding (8501 for dashboard, 8888 for Jupyter), post-start validation script
- Codespaces launches and runs `streamlit run dashboard/app.py` successfully

---

## ATT-009: Dashboard Not Verified Executable

**Severity**: MEDIUM  
**Category**: Assessment Infrastructure  
**Evidence**: `dashboard/app.py` exists (149 lines) but `streamlit run dashboard/app.py` never tested in audit

**Acceptance Criteria**: Dashboard launches, loads all 4 track checkpoints, displays metrics, exports CSV

---

## ATT-010: Track 2 Notebooks — Diffusion Training Missing, GNN Limited, NLP Synthetic Only

**Severity**: MEDIUM  
**Category**: Notebook Quality  
**Evidence**: 
- `05_generative.ipynb`: Diffusion = concept only (ATT-003)
- `08_gnn.ipynb`: Executable but only GCN/GAT/GraphSAGE on Cora (single dataset)
- `07_nlp_finetune.ipynb`: Executable but synthetic data only, no real dataset evaluation

**Acceptance Criteria**:
- Diffusion training loop in `05_generative.ipynb`
- GNN notebook extended with additional datasets/tasks
- NLP fine-tune uses real dataset (e.g., Alpaca, Dolly) with evaluation

---

## ATT-011: No CI/CD GitHub Actions for Automated Assessment

**Severity**: HIGH  
**Category**: CI/CD  
**Evidence**: No `.github/workflows/` directory exists; `BADGES.md` references CI but no workflow file

**Acceptance Criteria**: 
- `.github/workflows/assessment.yml` runs `pytest --nbval` on PR
- Workflow validates checkpoints, runs unit tests, publishes test artifacts
- Badge in README shows CI status

---

## ATT-012: No Linting/Formatting Config (ruff, black, pre-commit)

**Severity**: LOW  
**Category**: Code Quality  
**Evidence**: No `pyproject.toml`, `.ruff.toml`, `.pre-commit-config.yaml`, or `ruff.toml` in repo root

**Acceptance Criteria**: 
- `ruff` config for linting
- `black` config for formatting  
- `pre-commit` hooks installed and passing

---

## ATT-013: Badge Placeholders Not Replaced (README, Notebooks)

**Severity**: LOW  
**Category**: Documentation  
**Evidence**: `README.md` contains `YOUR_USER` placeholder; no badges embedded in any `.ipynb` files

**Acceptance Criteria**:
- README badges updated with actual repo/user
- Colab/Kaggle/Codespaces badges embedded in all 32 notebooks
- Zero-setup execution verified on at least one platform

---

## Summary

| Severity | Count | Tickets |
|----------|-------|---------|
| CRITICAL | 3 | ATT-001, ATT-002, ATT-003 |
| HIGH | 4 | ATT-004, ATT-005, ATT-006, ATT-011 |
| MEDIUM | 4 | ATT-007, ATT-008, ATT-009, ATT-010 |
| LOW | 2 | ATT-012, ATT-013 |
| **Total** | **13** | |

---

## Recommended Execution Order

1. **ATT-001** (blocker for all notebook execution)
2. **ATT-003** (critical Track 2 gaps)
3. **ATT-005** (assessment infra — enables verification)
4. **ATT-002** (capstone — journey completion requirement)
5. **ATT-004** (Track 4 depth)
6. **ATT-006** (Track 2 quality)
7. **ATT-011** (CI/CD)
8. **ATT-007, ATT-008, ATT-009, ATT-010** (DevOps polish)
9. **ATT-012, ATT-013** (code quality, docs)