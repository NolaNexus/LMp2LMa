# Multi-stage DevContainer for the ML Architect Journey
# `dev` is the default (CPU) target; `gpu-dev` adds CUDA-enabled PyTorch.

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential git curl graphviz \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspaces/LMp2LMa

COPY requirements-ci.txt requirements-assessment.txt ./
RUN pip install --upgrade pip \
    && pip install --extra-index-url https://download.pytorch.org/whl/cpu \
        -r requirements-ci.txt -r requirements-assessment.txt

COPY . .
RUN pip install -e . || true

# ---------------------------------------------------------------- dev (CPU)
FROM base AS dev

RUN python tools/validate_notebooks.py

CMD ["bash"]

# ---------------------------------------------------------------- dev (GPU)
FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04 AS gpu-dev

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3.12 python3.12-venv python3-pip build-essential git curl graphviz \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspaces/LMp2LMa

COPY requirements-ci.txt requirements-assessment.txt ./
RUN python3 -m pip install --upgrade pip \
    && python3 -m pip install -r requirements-ci.txt -r requirements-assessment.txt

COPY . .
RUN python3 -m pip install -e . || true

CMD ["bash"]