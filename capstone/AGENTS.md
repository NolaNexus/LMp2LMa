# Capstone — ML Programmer to ML Architect

## Purpose
Synthesize all journey learnings into a comprehensive ML architecture project.

## Objective
Design, implement, and document a production-ready ML system demonstrating mastery across foundations, MLOps, architecture, and specialization.

## Requirements
- **End-to-end**: Data ingestion → training → deployment → monitoring
- **Architecture**: ADRs, system diagrams, tradeoff analysis
- **MLOps**: CI/CD, model registry, automated testing, rollback
- **Scalability**: Distributed training or high-throughput serving
- **Specialization**: Domain-specific optimization
- **Documentation**: Runbooks, API specs, model cards, runbooks

## Suggested Project Structure
```
capstone/
├── data/              # Data pipelines, validation
├── training/          # Training code, configs, experiments
├── serving/           # Model serving, API, client SDK
├── infrastructure/    # IaC, Kubernetes manifests, CI/CD
├── monitoring/        # Dashboards, alerts, drift detection
├── docs/              # ADRs, architecture, runbooks
└── tests/             # Unit, integration, contract tests
```

## Deliverables
1. **Architecture Document** — system overview, data flow, component diagram
2. **ADRs** — 5+ key architectural decisions with context/alternatives
3. **Working System** — deployed and demonstrable
4. **Operations Guide** — deployment, scaling, incident response
5. **Retrospective** — what worked, what didn't, future improvements

## Evaluation Criteria
- Architectural coherence and justification
- Production readiness (monitoring, reliability, security)
- Code quality and testing
- Documentation completeness
- Demonstration of specialization depth