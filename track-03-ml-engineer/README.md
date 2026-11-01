# Module 2: MLOps & ML Engineering

**Maps to Skillsoft Track 3: ML Engineer** — 17 courses | ~16h

## Focus
Predictive modeling, analytics, ML modeling, ML architecting, production deployment

## Key Topics
1. **Advanced Predictive Modeling**
   - Ensemble methods (bagging, boosting, stacking)
   - XGBoost, LightGBM, CatBoost
   - Model selection & comparison frameworks

2. **ML System Design & Architecture**
   - Scalable ML system design patterns
   - Feature stores (Feast, Tecton)
   - Model serving architectures (batch, real-time, streaming)

3. **Production ML Engineering**
   - CI/CD for ML (GitHub Actions, GitLab CI, Jenkins)
   - Model packaging & deployment (Docker, KServe, BentoML, Seldon)
   - A/B testing, canary deployments, shadow mode

4. **MLOps Platform & Tooling**
   - MLflow advanced: projects, models, registry, deployment
   - Kubeflow Pipelines / Vertex AI Pipelines / Airflow
   - Data & model versioning (DVC, Git LFS, lakeFS)

5. **Monitoring & Observability**
   - Data drift / concept drift detection (Evidently, WhyLabs)
   - Model performance monitoring
   - Feature importance & attribution in production

6. **Reliability & Governance**
   - Model cards, datasheets, model registry governance
   - Automated testing (data, model, pipeline tests)
   - Compliance, audit trails, reproducibility

## Prerequisites
- Module 1 complete (data pipelines, experiment tracking, evaluation)
- Docker basics, Git, CI/CD fundamentals
- Cloud basics (AWS/GCP/Azure) — one provider

## Notebooks
| # | Notebook | Description |
|---|----------|-------------|
| 01 | `01_ensemble_modeling.ipynb` | Stacking, blending, voting classifiers; model selection |
| 02 | `02_feature_store.ipynb` | Feast local registry; feature definitions, materialization |
| 03 | `03_mlflow_advanced.ipynb` | MLflow Projects, model registry, model serving, deployment |
| 04 | `04_kubeflow_pipeline.ipynb` | End-to-end Kubeflow pipeline with components, caching |
| 05 | `05_model_serving.ipynb` | FastAPI + BentoML + Docker; batch & REST endpoints |
| 06 | `06_drift_monitoring.ipynb` | Evidently AI data drift reports; scheduled monitoring |
| 07 | `07_ci_cd_ml.ipynb` | GitHub Actions: test → build → deploy to staging |
| 08 | `08_governance.ipynb` | Model cards, automated validation gates, audit logs |

## Tools to Learn
- MLflow (advanced), Kubeflow, Feast, Evidently AI
- BentoML / Seldon / KServe, Docker, Kubernetes basics
- GitHub Actions / GitLab CI, DVC, Great Expectations (advanced)
- Prometheus/Grafana for ML metrics

## Deliverables
- Reproducible Kubeflow/MLflow pipeline deploying a model to local K8s (kind/k3d)
- Drift monitoring dashboard with alerts
- CI/CD pipeline with automated model validation gates
- Documented model card for the deployed model