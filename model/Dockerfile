# CUDA 12.4 + cuDNN + Python 3.10 for GPU model serving
FROM nvidia/cuda:12.4.1-cudnn-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

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

COPY requirements.txt ./
RUN python3 -m pip install -r requirements.txt

COPY main.py ./

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
