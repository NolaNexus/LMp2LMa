# ML Architect Journey - Multi-stage Dev Environment
# Build: docker build -t ml-architect-journey .
# Run: docker run -it --gpus all -v $(pwd):/workspace ml-architect-journey

FROM nvidia/cuda:12.1-devel-ubuntu22.04 AS base
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 python3.10-venv python3-pip git curl && \
    rm -rf /var/lib/apt/lists/*

FROM base AS cpu-dev
WORKDIR /workspace
COPY requirements.txt requirements-ci.txt ./
RUN pip install --upgrade pip && pip install -r requirements-ci.txt

FROM base AS gpu-dev
WORKDIR /workspace
COPY requirements-gpu.txt ./
RUN pip install --upgrade pip && pip install -r requirements-gpu.txt

# Default target
FROM gpu-dev AS dev
CMD ["bash"]
