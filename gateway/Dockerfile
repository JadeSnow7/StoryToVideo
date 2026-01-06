# Gateway Dockerfile - Lightweight Version
# Does NOT use environment.yml (that's for Model with GPU deps)
# Gateway only needs: fastapi, uvicorn, httpx, ffmpeg

FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies (lightweight, no GPU libs)
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy gateway code
COPY . /app/

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run gateway
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
