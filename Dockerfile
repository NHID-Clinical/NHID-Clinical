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

# Build dependencies into a self-contained prefix.
#
# `pip install --user` puts them in /root/.local, which the final stage then
# copied and tried to read as USER nhid. /root is mode 700, so a non-root user
# cannot traverse it: every import failed. Installing to a neutral prefix and
# copying it onto /usr/local avoids the problem rather than papering over it
# with chmod.
COPY requirements.txt .
RUN pip install --prefix=/install --no-cache-dir -r requirements.txt

# Final production image
FROM python:3.13-slim

WORKDIR /app

# Install runtime system dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Site-packages land in /usr/local, readable by every user in the image.
COPY --from=builder /install /usr/local

# Application code.
#
# The root-level modules are the ASGI application: main.py mounts the API
# routers and the voice pipeline, and its import closure reaches app.py,
# nhid_policy.py, llm.py, nhid_event_store.py and twilio_helper.py. None of
# them used to be copied, so the image could not have started even with a
# correct CMD.
COPY main.py app.py llm.py twilio_helper.py ./
COPY nhid_api_auth.py nhid_api_endpoints.py nhid_attest.py ./
COPY nhid_audit_export.py nhid_event_store.py nhid_payer.py nhid_policy.py ./

COPY src/ ./src/
COPY functions/ ./functions/
COPY adapters/ ./adapters/
COPY schema/ ./schema/

# tests/ and scripts/ are RUNTIME dependencies here, not test baggage:
#   * src/cts_runner.py loads tests/nhid_conformance_test_suite_v1.yaml, which
#     is what POST /v1/cts/evaluate runs;
#   * src/cli.py imports scripts/export_evidence_pack.py and src/pilot_pdf.py
#     imports scripts/generate_pdfs.py.
# Removing either breaks a shipped feature. Check those call sites before
# trimming this.
COPY tests/ ./tests/
COPY scripts/ ./scripts/

# Corpus for the docs reading aid mounted by main.py (src/nhid_spec_rag.py).
# It degrades gracefully when absent, so this is for function, not startup.
COPY docs/ ./docs/

COPY .env.example* ./

# Audit storage and the writable paths the app derives from its own root.
RUN mkdir -p /data /app/logs && \
    chmod 755 /data

# Create non-root user for security
RUN useradd -m -u 1000 nhid && \
    chown -R nhid:nhid /app /data

USER nhid

# Health check: GET /health is served by main:app.
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

# main:app is the ASGI application.
#
# This was `functions.handler:app`, which does not exist — functions/handler.py
# is an AWS Lambda entry point exposing `lambda_handler(event, context)` and no
# ASGI object, so uvicorn exited with "Attribute 'app' not found in module".
# main:app is also the app that serves the /health path the HEALTHCHECK above
# probes. The Lambda surface is deployed from template.yaml, not from here.
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
