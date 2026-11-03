# ML Programmer → ML Architect Aspire Journey

**Skillsoft Aspire Journey**: [ML Programmer to ML Architect](https://www.skillsoft.com/journey/ml-programmer-to-ml-architect-17eeca71-f2bd-4558-8d0f-df7d0122139a)

## Repository Structure (aligned to Skillsoft Tracks)

| Track | Skillsoft Track | Courses | Hours | Notebooks | Status |
|-------|-----------------|---------|-------|-----------|--------|
| **Track 1** | ML Programmer (Foundations) | 25 | 21h 56m | 7 | ✅ Complete |
| **Track 2** | DL Programmer (Specialization) | 21 | 21h 1m | 11 | 🔄 In Progress |
| **Track 3** | ML Engineer (MLOps) | 17 | 16h 13m | 8 | ✅ Complete |
| **Track 4** | ML Architect (Architecture) | 12 | 12h 22m | 6 | ✅ Complete |
| **Integration** | Capstone | — | — | — | ✅ Complete |

**Overall Coverage**: ~48% (75 courses, 71h 35m total)

---

## Quick Start

### Zero-Setup (Browser)
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/NolaNexus/LMp2LMa/blob/master/)
[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/NolaNexus/LMp2LMa?devcontainer_path=.devcontainer/devcontainer.json)

### Local (CPU)
```bash
pip install -r requirements.txt
```

### Local (GPU)
```bash
pip install -r requirements-gpu.txt
```

> **Maxwell GPU hosts (Quadro M5000, sm_52):** install the CUDA 12.6 stack instead.
> CUDA 13 wheels contain no sm_52 kernels and fail at runtime with
> `no kernel image is available for execution on the device`.
> ```bash
> pip install --index-url https://download.pytorch.org/whl/cu126 -r requirements-gpu-cu126.txt
> ```
> NVIDIA driver branch 580.x is the last branch supporting Maxwell; do not install
> `nvidia-utils`/`nvidia-open` 595 or newer on these machines. See
> `requirements-gpu-cu126.txt` for details.
>
> Maxwell (sm_52) limits: no bf16, no TF32, no tensor cores, no FlashAttention;
> `torch.compile`/Triton requires sm_70+ (set `TORCHDYNAMO_DISABLE=1`).
> PyTorch GPU support for this card is frozen at 2.14.1+cu126.

### Docker
```bash
docker compose up -d gpu-dev
docker compose exec gpu-dev bash
```

### Dashboard
```bash
streamlit run dashboard/app.py
# Open http://localhost:8501
```

---

## Assessment

```bash
# Run full assessment (pytest + nbval + checkpoints)
python tests/run_assessment.py

# Validate notebooks only
pytest --nbval --nbval-lax track-01-ml-programmer/

# Run unit tests
pytest tests/ -v
```

---

## Track Details

### Track 1: ML Programmer (Foundations) — `track-01-ml-programmer/`
| Notebook | Skillsoft Courses | Skills |
|----------|-------------------|--------|
| `01_data_preprocessing.ipynb` | Building Training Sets, Preprocessing for Regression/Classification, Model Management: Pipelines | Data pipelines, Great Expectations, joblib |
| `02_experiment_tracking.ipynb` | Model Management: Production, Linear Regression Scikit/Keras | MLflow tracking, GridSearchCV, Model Registry |
| `03_model_evaluation.ipynb` | Linear Models: Managing, Gradient Descent & Regularization | Cross-validation, learning curves, calibration, fairness |
| `04_mathematical_foundations.ipynb` | Linear Algebra Fundamentals, Advanced Linear Algebra, Math for Data Science, Gradient Descent | SVD, PCA, Probability (CLT, Bayes), GD, MLE/MAP |
| `05_computational_theory.ipynb` | Computational Theory: Finite Automata, Turing/Complexity | DFA/NFA, Turing machines, P vs NP, SAT, CFG (CYK) |
| `06_bayesian_methods.ipynb` | Bayesian Concepts, PyMC Computation, Advanced Bayesian | Bayes theorem, MLE/MAP, PyMC3 MCMC, UQ |
| `07_reinforcement_learning.ipynb` | RL Essentials, RL Tools | MDP, Q-learning, ε-greedy, Grid World, Gym |

### Track 2: DL Programmer (Specialization) — `track-02-dl-programmer/`
| Notebook | Skillsoft Courses | Skills |
|----------|-------------------|--------|
| `01_nn_fundamentals.ipynb` | NN: Biological & Artificial, Perceptrons | Perceptrons, backprop, initialization |
| `02_cnn_vision.ipynb` | CNNs: Intro, Advanced | Conv, pooling, ResNet, transfer learning |
| `03_rnn_seq.ipynb` | RNNs: Intro, LSTM/GRU | RNN/LSTM/GRU, sequence modeling, attention |
| `04_transformers.ipynb` | Transformers: Attention, BERT | Self-attention, multi-head, BERT, positional encoding |
| `05_generative.ipynb` | Generative: VAE/GAN, Diffusion | VAE (ELBO), GAN (minimax), Diffusion |
| `06_self_supervised.ipynb` | Self-Supervised | SimCLR, BYOL, MAE, contrastive learning |
| `07_nlp_finetune.ipynb` | NLP Fine-tuning | QLoRA, 4-bit, PEFT, instruction tuning |
| `08_gnn.ipynb` | GNN | Message passing, GCN/GAT, PyG |
| `09_time_series.ipynb` | Time Series (3 courses) | NeuralForecast, Prophet, Hierarchical, MinTrace |
| `10_recommender_systems.ipynb` | Recommenders (2 courses) | Two-tower, TFRS, Faiss ANN, BPR, Cold start |
| `11_science_healthcare.ipynb` | Science/Healthcare (2 courses) | UQ, Domain adaptation, Clinical trials |

### Track 3: ML Engineer (MLOps) — `track-03-ml-engineer/`
| Notebook | Skillsoft Course | Skills |
|----------|------------------|--------|
| `01_ensemble_modeling.ipynb` | Ensemble Modeling | Voting, Stacking, XGBoost/LightGBM/CatBoost, MLflow |
| `02_feature_store.ipynb` | Feature Store (Feast) | Feast init/apply/materialize, online retrieval |
| `03_mlflow_advanced.ipynb` | MLflow Advanced | Projects, Registry, Comparison, Autolog |
| `04_kubeflow_pipeline.ipynb` | Kubeflow Pipelines | KFP v2, Components, Pipeline, YAML, DAG |
| `05_model_serving.ipynb` | Model Serving | BentoML, FastAPI `/predict`, HTTP serving |
| `06_drift_monitoring.ipynb` | Drift Monitoring | Evidently AI, Data/Target/Prediction drift, Alerting |
| `07_ci_cd_ml.ipynb` | CI/CD for ML | GitHub Actions, Validation gates, Artifacts |
| `08_governance.ipynb` | Governance | Model cards, Audit logs, Compliance, Gates |

### Track 4: ML Architect (Architecture) — `track-04-ml-architect/`
| Notebook | Skillsoft Course | Skills |
|----------|------------------|--------|
| `01_distributed_training.ipynb` | Distributed Training | FSDP, DeepSpeed, Scaling laws, Comm overhead |
| `02_triton_serving.ipynb` | Triton Serving | Triton server, Model repo, Inference, P95 bench |
| `03_quantization.ipynb` | Quantization | Dynamic int8, Static quant, AMP, Size/accuracy |
| `04_platform_design.ipynb` | Platform Design | Requirements → Tradeoffs → 5+ ADRs |
| `05_cost_optimization.ipynb` | Cost Optimization | Spot strategies, GPU utilization, Cross-cloud (9 GPUs) |
| `06_foundation_model_finetune.ipynb` | Foundation Model Fine-tuning | 4-bit quant, LoRA/QLoRA, 97% param reduction |

### Integration: Capstone — `capstone/`
- `README.md`: 5 themes, 9-step roadmap, Evaluation criteria (Arch 25%, Model 20%, Eng 25%, Gov 15%, Comm 15%)

---

## Assessment Infrastructure

- **`tests/`**: pytest + nbval notebook validation
- **`checkpoints/`**: Skill checkpoints per track (JSON, auto-graded)
- **`dashboard/`**: Streamlit progress tracking dashboard
- **`requirements*.txt`**: CPU/GPU/CI variants with lock files
- **`.devcontainer/Dockerfile`**: single multi-stage dev image (dev / gpu-dev) used by both Codespaces and `docker compose`
- **`BADGES.md`**: Colab/Kaggle/Codespaces badge templates

---

## Progress Tracking

Run the dashboard:
```bash
streamlit run dashboard/app.py
```

Features:
- Track-level notebook/checkpoint completion
- Per-checkpoint question browser
- Final exam specifications
- CSV export for reporting

---

## Cross-Reference: Skillsoft Course → Notebook

See `~/.opencode/plan/plan_0001-curriculum-remediation.md` for the full 75-course cross-reference matrix (kept outside the repo, alongside the other plans).

---

## License

Educational use per Skillsoft Aspire Journey terms.
