# ADR-004: Deployment - Kubernetes with GitOps (ArgoCD)

**Status**: Accepted
**Date**: 2026-11-01
**Deciders**: ML Architect Team
**Technical Story**: Define deployment strategy and infrastructure as code

## Context

Deployment requirements:
- Cloud-agnostic (AWS/GCP/Azure/on-prem)
- Blue-green and canary deployments
- Rollback in <30 seconds
- Infrastructure as Code (IaC)
- Policy enforcement (security, resource limits)
- Cost visibility and optimization
- Multi-environment (dev, staging, prod)

## Decision

**Kubernetes with GitOps via ArgoCD**:

- **Cluster**: EKS/GKE/AKS managed control plane
- **GitOps**: ArgoCD for continuous deployment from Git
- **IaC**: Terraform for cluster + Helm for applications
- **Service Mesh**: Istio for mTLS, traffic splitting, observability
- **Secrets**: External Secrets Operator + Vault/Secrets Manager
- **Monitoring**: Prometheus/Grafana stack (kube-prometheus-stack)
- **Logging**: Loki + Promtail
- **Cost**: Kubecost for allocation

## Consequences

**Positive**:
- Declarative desired state (self-healing)
- Audit trail via Git history
- Progressive delivery (canary, blue-green)
- Cloud portability
- Policy enforcement via OPA/Gatekeeper
- Rich ecosystem

**Negative**:
- Operational complexity (mitigated by managed clusters)
- Learning curve for team
- Resource overhead (control plane + agents)
- Debugging distributed system challenges

## Alternatives Considered

1. **VMs + Ansible**: Simpler but no self-healing, harder scaling
2. **ECS/Fargate**: AWS lock-in, less flexible
3. **Cloud Run/Cloud Functions**: Good for stateless, limited for ML workloads
4. **Nomad**: Simpler but smaller ecosystem

## Implementation Notes

```
capstone/infrastructure/
├── terraform/           # Cluster provisioning
│   ├── modules/
│   │   ├── eks/
│   │   ├── gke/
│   │   └── networking/
│   └── environments/
│       ├── dev/
│       ├── staging/
│       └── prod/
├── helm/                # Application charts
│   ├── customer-support/
│   ├── monitoring/
│   └── platform/
├── argocd/              # ArgoCD applications
│   ├── applications/
│   └── projects/
└── policies/            # OPA/Gatekeeper policies
```

- `capstone/infrastructure/terraform/` - multi-cloud modules
- `capstone/infrastructure/helm/customer-support/` - app chart with values per env
- `capstone/infrastructure/argocd/` - Application resources
- CI/CD: GitHub Actions → build/push images → update Helm values in Git → ArgoCD syncs