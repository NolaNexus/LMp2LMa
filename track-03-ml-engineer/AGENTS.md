# Module 2: MLOps — ML Programmer to ML Architect

## Purpose
Operationalize ML models: deployment, monitoring, CI/CD, and lifecycle management.

## Learning Objectives
- Design and implement ML model deployment architectures
- Build CI/CD pipelines for ML workflows
- Implement model monitoring and drift detection
- Manage model lifecycle from training to retirement

## Key Topics
1. **Model Serving** — REST/gRPC, batch vs online, model servers (Triton, TorchServe, TF Serving)
2. **CI/CD for ML** — GitHub Actions, GitLab CI, Argo, Kubeflow Pipelines
3. **Monitoring** — data drift, concept drift, performance degradation, alerting
4. **Feature Stores** — Feast, Tecton, offline/online stores
5. **Infrastructure** — Kubernetes, KServe, Kubeflow, cloud ML platforms
6. **Governance** — model registry, lineage, compliance, rollback strategies

## Suggested Exercises
- Deploy a model as a REST API with autoscaling
- Build a CI/CD pipeline: train → test → register → deploy
- Implement drift detection with statistical tests
- Set up a feature store for a sample use case
- Create a model registry with promotion workflows

## Tools to Learn
- Docker, Kubernetes (kind/k3d for local)
- MLflow Model Registry, Kubeflow Pipelines
- Prometheus/Grafana for monitoring
- Evidently AI or WhyLabs for drift detection
- Feast for feature store

## Deliverables
- Containerized model serving solution
- Working CI/CD pipeline YAML
- Monitoring dashboard with alerts
- Documented rollback procedure