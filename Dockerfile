# NHID-Clinical Compliance Audit Engine
# Multi-stage build for production-ready Docker image

FROM python:3.13-slim AS builder

WORKDIR /build

# Install system dependencies for building
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and build wheels
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Final production image
FROM python:3.13-slim

WORKDIR /app

# Install runtime system dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY src/ ./src/
COPY functions/ ./functions/
COPY adapters/ ./adapters/
COPY tests/ ./tests/
COPY scripts/ ./scripts/
COPY .env.example* ./

# Create audit storage directory with proper permissions
RUN mkdir -p /data && \
    chmod 755 /data

# Create non-root user for security
RUN useradd -m -u 1000 nhid && \
    chown -R nhid:nhid /app /data

USER nhid

# Health check: verify audit store connectivity
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port for Lambda/API
EXPOSE 8000

# Default: run Lambda adapter with FastAPI
CMD ["python", "-m", "uvicorn", "functions.handler:app", "--host", "0.0.0.0", "--port", "8000"]
