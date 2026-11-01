# Module 3: Architecture — ML Programmer to ML Architect

## Purpose
Design scalable, maintainable ML systems: system design, distributed training, and platform architecture.

## Learning Objectives
- Architect end-to-end ML platforms and systems
- Design for scalability, reliability, and cost-efficiency
- Implement distributed training and inference patterns
- Make informed technology choices for ML infrastructure

## Key Topics
1. **System Design** — requirements gathering, capacity planning, tradeoffs
2. **Distributed Training** — data/model/pipeline parallelism, Horovod, DeepSpeed, FSDP
3. **Serving Architecture** — latency vs throughput, batching, caching, model composition
4. **Data Architecture** — lakehouse, streaming, real-time features, Kappa/Lambda
5. **Platform Engineering** — internal ML platforms, self-serve infrastructure
6. **Cost Optimization** — GPU utilization, spot instances, model compression

## Suggested Exercises
- Design an ML platform for a hypothetical company (requirements → architecture diagram)
- Implement distributed training for a large model
- Build a low-latency serving stack with batching/caching
- Compare cloud ML services (Vertex AI, SageMaker, Azure ML)
- Optimize a training job for cost/performance

## Tools to Learn
- Distributed training: PyTorch Distributed, DeepSpeed, Accelerate
- Serving: Triton, vLLM, TGI, BentoML
- Orchestration: Airflow, Dagster, Prefect
- Infrastructure: Terraform, Helm, ArgoCD
- Profiling: Nsight, PyTorch Profiler, TensorBoard

## Deliverables
- Architecture decision records (ADRs) for key choices
- System design document with diagrams
- Working distributed training script
- Benchmark results for serving optimizations