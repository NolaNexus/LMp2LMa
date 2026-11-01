# Module 3: ML Architecture

**Maps to Skillsoft Track 4: ML Architect** — 12 courses | ~12h

## Focus
Applied predictive modeling, CNNs/RNNs at scale, ML system architecture, strategic decision-making

## Key Topics
1. **Architectural Patterns for ML Systems**
   - Online vs batch vs streaming inference
   - Lambda / Kappa architectures for ML
   - Event-driven ML systems (Kafka, Flink, Redis)

2. **Distributed Training & Scaling**
   - Data parallelism, model parallelism, pipeline parallelism
   - Horovod, DeepSpeed, FSDP, Ray Train
   - Multi-GPU / multi-node training strategies

3. **Large-Scale Model Serving**
   - TensorRT, ONNX Runtime, Triton Inference Server
   - Model quantization, distillation, pruning
   - Dynamic batching, request scheduling, KV caching

4. **ML Platform Design**
   - Platform-as-a-product thinking
   - Multi-tenancy, isolation, resource quotas
   - Self-serve ML platform components

5. **Advanced Deep Learning Architectures**
   - Transformers, attention mechanisms (from Track 2, applied at scale)
   - Efficient transformers (FlashAttention, LoRA, QLoRA)
   - Foundation model fine-tuning patterns

6. **Strategic ML Architecture Decisions**
   - Build vs buy: cloud AI services vs custom
   - Cost optimization (GPU utilization, spot instances)
   - Team structure: ML platform vs applied ML vs research

## Prerequisites
- Module 2 complete (MLOps, production patterns)
- Solid Python, PyTorch/TensorFlow, distributed systems basics
- Kubernetes fundamentals (pods, services, operators)

## Notebooks
| # | Notebook | Description |
|---|----------|-------------|
| 01 | `01_distributed_training.ipynb` | FSDP/DeepSpeed on multi-GPU; scaling laws |
| 02 | `02_triton_serving.ipynb` | Triton Inference Server: ensemble, model pipeline |
| 03 | `03_quantization.ipynb` | ONNX quantization, TensorRT optimization, benchmarking |
| 04 | `04_platform_design.ipynb` | Architecture decision records (ADRs) for ML platform |
| 05 | `05_cost_optimization.ipynb` | Spot instance training, GPU scheduling, cost modeling |
| 06 | `06_foundation_model_finetune.ipynb` | LoRA/QLoRA on LLM; PEFT; evaluation at scale |

## Tools to Learn
- PyTorch Distributed (FSDP, DDP), DeepSpeed, Ray
- Triton Inference Server, TensorRT, ONNX Runtime
- Kubernetes operators (Kubeflow, KServe), Helm
- LoRA/PEFT (Hugging Face), bitsandbytes

## Deliverables
- Distributed training run on 2+ GPUs with scaling analysis
- Optimized model served via Triton with latency/throughput benchmarks
- Architecture decision records (ADRs) for a hypothetical ML platform
- Cost model for training/serving at scale