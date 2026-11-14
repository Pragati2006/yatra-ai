# ==============================================================================
# Yatra AI — Production Container for Hugging Face Spaces & Render
# Multi-platform Python ASGI container for FastAPI + LangChain
# ==============================================================================

FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_ENV=production \
    ENV=production \
    PORT=7860 \
    HOST=0.0.0.0 \
    DATA_DIR=/app/data

WORKDIR /app

# Install minimal system dependencies (curl for container healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source tree
COPY . /app/

# Hugging Face Spaces runs as non-root UID 1000 ("user")
# Create non-root user and ensure read/write access to /app/data
RUN mkdir -p /app/data && \
    useradd -m -u 1000 user && \
    chown -R user:user /app

USER user

# Default Hugging Face Spaces port
EXPOSE 7860

# Container liveness health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT:-7860}/api/health || exit 1

# Launch FastAPI via uvicorn reading dynamic PORT
CMD ["python", "-m", "backend.main"]
