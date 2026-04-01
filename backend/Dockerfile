# GPU-enabled backend with CUDA 12.8 support (compatible with RTX 5060 / Blackwell)
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install PyTorch with CUDA 12.8 support (includes compute capability sm_120)
# This must be done BEFORE installing other requirements to avoid conflicts
RUN pip install --no-cache-dir \
    torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128

COPY requirements.txt .

# Install remaining requirements (transformers, fastapi, etc.)
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
