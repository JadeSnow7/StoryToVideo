# CUDA 12.4 + cuDNN + Python 3.10 for GPU model serving
FROM nvidia/cuda:12.4.1-cudnn-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    MODEL_ROOT=/workspace

WORKDIR /workspace

# System deps
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       python3.10 python3.10-venv python3-pip git curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install torch with CUDA 12.4 wheels
RUN python3 -m pip install --upgrade pip \
    && python3 -m pip install \
       torch==2.4.0 torchvision==0.19.0 torchaudio==2.4.0 \
       --index-url https://download.pytorch.org/whl/cu124

COPY requirements.txt ./model/requirements.txt
RUN python3 -m pip install -r model/requirements.txt

COPY . ./model
ENV PYTHONPATH="/workspace"

EXPOSE 8000

CMD ["uvicorn", "model.main:app", "--host", "0.0.0.0", "--port", "8000"]
