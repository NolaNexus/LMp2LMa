# Capstone Project: ML System Integration

**Integration of all 4 modules** — Self-paced (~2-4 weeks)

## Goal
End-to-end ML system demonstrating ML Architect competency: foundations → MLOps → architecture → specialization integration.

## Project Structure
```
capstone/
├── data/                    # Data ingestion, validation, feature store
├── training/                # Training code, configs, experiments (MLflow)
├── serving/                 # Model serving, FastAPI + Triton, client SDK
├── infrastructure/          # IaC (Terraform/Helm), Kubernetes manifests, CI/CD
├── monitoring/              # Dashboards (Grafana/Prometheus), alerts, drift detection
├── docs/                    # ADRs, architecture diagrams, runbooks
├── governance/              # Model cards, audit logs, compliance artifacts
├── tests/                   # Unit, integration, contract, data validation tests
├── reports/                 # Evaluation results, feature importance, error analysis
├── requirements.txt
├── README.md
└── Makefile
```

## Suggested Capstone Themes (Choose ONE)

### Theme 1: Real-time Fraud Detection
- **Domain**: Financial services transaction fraud
- **Architecture**: Streaming (Kafka/Flink) → Feature Store (Feast) → Online Model (Triton) → Monitoring
- **ML**: XGBoost + Neural Net ensemble, online learning with shadow mode
- **Scale**: 100K+ transactions/sec, <10ms latency requirement
- **Key Challenges**: Concept drift, class imbalance, explainability, latency vs. accuracy tradeoff

### Theme 2: E-commerce Recommendation System
- **Domain**: Product recommendation for e-commerce platform
- **Architecture**: Two-tower (user/item) → ANN Index (Faiss/ScaNN) → Real-time re-ranking → Batch offline evaluation
- **ML**: Collaborative filtering + content-based features + LightGCN graph neural network
- **Scale**: 10M+ users, 1M+ items, real-time personalization per session
- **Key Challenges**: Cold start, item freshness, recommendation diversity, implicit feedback

### Theme 3: Document Intelligence Pipeline
- **Domain**: Insurance claim processing (automated data extraction)
- **Architecture**: Multimodal (LayoutLMv3) → Structured extraction → Validation rules → Human-in-the-loop review
- **ML**: Document classification, NER (named entity recognition), table extraction, VQA (visual question answering)
- **Scale**: 100K+ docs/day, 80% auto-processed, 20% human review
- **Key Challenges**: Layout variability, OCR errors, domain adaptation, ambiguity resolution

### Theme 4: Time-Series Forecasting at Scale
- **Domain**: Retail demand forecasting across 1M+ SKUs
- **Architecture**: Hierarchical forecasting (global + local models) → Feature store with time features → Batch + real-time prediction endpoints
- **ML**: DeepAR + Temporal Fusion Transformer (TFT) + ensemble with statistical baselines (ETS, Prophet)
- **Scale**: 1M+ SKUs, multiple forecasting horizons (daily/weekly/monthly), exogenous variables (promotions, weather)
- **Key Challenges**: Hierarchical reconciliation, cold start, model drift, cost optimization

### Theme 5: LLM-powered Customer Support Application
- **Domain**: Automated customer support with RAG (Retrieval-Augmented Generation)
- **Architecture**: Vector DB (Qdrant/FAISS) → Retriever → Fine-tuned LLM (QLoRA) → Guardrails → Evaluation
- **ML**: LoRA/QLoRA fine-tuned LLM + semantic retrieval + prompt engineering + RLHF signals
- **Scale**: 10K+ queries/day, multi-turn conversations, citation tracking
- **Key Challenges**: Hallucination, latency, cost per query, evaluation groundedness, privacy

## Core Requirements (All Themes Must Address)

1. **Problem Definition** with business context and success metrics
2. **Data Engineering**: Ingestion pipelines, Great Expectations validation, Feature Store (Feast)
3. **Model Development**: Multiple approaches (classical + DL), experiment tracking (MLflow), comparison
4. **Architecture**: ADRs (Architecture Decision Records) for key tradeoffs, system diagram
5. **Production Pipeline**: CI/CD (GitHub Actions/GitLab CI), automated testing, deployment (Docker + kind/k3d or cloud), rollback
6. **Governance**: Model cards, audit logs, drift detection (Evidently AI), retraining triggers
7. **Documentation**: Architecture diagram, runbooks, cost analysis, handoff guide, model cards

## Deliverables

### 1. Architecture Document (20%)
- System overview with data flow diagram
- Component diagram (ingestion → training → serving → monitoring)
- Deployment topology (local kind/k3d, cloud GCP/AWS/Azure, or hybrid)
- Scalability & cost analysis

### 2. ADRs (Architecture Decision Records) — 5+ entries (25%)
Each ADR follows this format:
- **Title**: Brief descriptive title
- **Status**: Proposed / Accepted / Deprecated
- **Context**: Problem situation and forces acting
- **Decision**: What was decided
- **Consequences**: Positive and negative outcomes
- **Alternatives Considered**: What else was evaluated

### 3. Working System (30%)
- Deployed and demonstrable end-to-end system
- API endpoint with sample requests and responses
- Monitoring dashboard showing live metrics
- Drift detection alerts configured

### 4. Operations Guide (15%)
- Deployment guide (local + cloud)
- Scaling instructions
- Incident response runbook
- Cost optimization recommendations

### 5. Retrospective (10%)
- What worked well
- What would change at 10x scale
- What would change with different team structure
- Technical debt & improvement priorities

## Getting Started — 9-Step Roadmap

1. **Choose theme** from above or propose your own (justified to course staff)
2. **Create project repo** with the structure above
3. **Set up MLflow + Feast + Triton** locally (kind/k3d Docker cluster) or cloud
4. **Implement data pipeline** with validation gates (Great Expectations)
5. **Train baseline models** (classical + deep learning) with full experiment tracking
6. **Build production pipeline** with CI/CD (train → test → register → deploy → monitor)
7. **Add monitoring & governance** (Prometheus + Grafana, Evidently drift, model cards)
8. **Document everything** (ADRs, model cards, runbooks, architecture diagram)
9. **Prepare demo & presentation** (30 min: problem → architecture → results → ops → lessons)

## Resources

- [MLOps Zoomcamp](https://github.com/DataTalksClub/mlops-zoomcamp) — Reference implementations
- [Feast Tutorials](https://docs.feast.dev/getting-started/) — Feature store patterns
- [Kubeflow Examples](https://github.com/kubeflow/examples) — Pipeline patterns
- [Triton Examples](https://github.com/triton-inference-server/tutorials) — Serving patterns
- [BentoML Examples](https://github.com/bentoml/BentoML/tree/main/examples) — Model packaging
- [Great Expectations](https://docs.greatexpectations.io/) — Data validation
- [Evidently AI](https://www.evidently.ai/) — Monitoring & drift detection
- [Faiss](https://github.com/facebookresearch/faiss) — Vector similarity search
- [PyCaret](https://pycaret.org/) — Classical ML comparison framework

## Evaluation Criteria

| Category | Weight | Criteria |
|----------|--------|----------|
| **Architecture** | 25% | ADRs, scalability, trade-offs documented, system coherence |
| **Model Quality** | 20% | Multiple approaches evaluated, proper baselines, valid results |
| **Engineering** | 25% | CI/CD, testing, deployment, monitoring, rollback procedures |
| **Governance** | 15% | Model cards, audit trail, drift detection, compliance readiness |
| **Communication** | 15% | Clear docs, presentation quality, retrospective insights |

## Getting Help

- Review each module's notebooks for patterns and tools
- Reference Skillsoft course IDs for cross-referencing concepts
- Form study groups for theme-specific challenges
- Post questions in the course forum with specific technical details