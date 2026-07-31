# Docker Deployment Guide: NHID-Clinical

This guide covers building and running NHID-Clinical in Docker for development, testing, and local pilot validation.

## Quick Start

### Prerequisites

- Docker 20.10+ (buildx for multi-stage builds)
- Docker Compose 2.0+
- Linux/macOS (Windows requires WSL2 or Docker Desktop)

### Run Locally with Docker Compose

```bash
cd /path/to/NHID-Clinical

# Build and start services
docker-compose up --build

# In another terminal, validate health
curl http://localhost:8000/health

# Test the conformance endpoint
curl -X POST http://localhost:8000/v1/adapters/vapi/check \
  -H "Content-Type: application/json" \
  -d @tests/demo_scenarios/vapi_noncompliant.json
```

### Stop Services

```bash
docker-compose down
```

### Clean Up Volumes (Remove Data)

```bash
docker-compose down -v
```

## Docker Architecture

### Image Structure

The NHID-Clinical Docker image uses a multi-stage build to minimize size:

1. **Builder Stage** (`python:3.13-slim`)
   - Installs build dependencies
   - Compiles Python packages with `pip install --user`
   - Produces lightweight wheel cache

2. **Production Stage** (`python:3.13-slim`)
   - Copies only runtime packages from builder
   - Installs curl for health checks
   - Creates non-root user (nhid:1000) for security
   - Exposes port 8000

### Services

#### nhid-api
- **Image**: Built from local Dockerfile
- **Port**: 8000 (FastAPI/uvicorn)
- **Volumes**:
  - `/data` - SQLite audit database (persistent)
  - `.` - Source code (development only, remove for production)
- **Health Check**: HTTP GET `/health` (30s interval)
- **Environment**:
  - `DEPLOYMENT_MODE=development`
  - `AUDIT_STORE_TYPE=sqlite`
  - `AUDIT_STORE_PATH=/data/audit_events.db`
  - `AUDIT_SECRET_KEY_B64` - HMAC secret (auto-generated if not set)
  - `LOG_LEVEL=INFO`

#### localstack
- **Image**: `localstack/localstack:latest`
- **Port**: 4566 (AWS API gateway)
- **Services**: S3, Lambda, Logs, API Gateway, DynamoDB, Secrets Manager
- **Data**: Mounted at `/tmp/localstack` (ephemeral by default)

## Environment Configuration

### .env.example

Create a `.env` file for local overrides:

```bash
cp .env.example .env
```

### Required Variables

```env
# Deployment mode: development, staging, production
DEPLOYMENT_MODE=development

# Audit store configuration
AUDIT_STORE_TYPE=sqlite          # sqlite | dynamodb (phase 6b)
AUDIT_STORE_PATH=/data/audit_events.db

# HMAC secret key (base64-encoded 32 bytes)
# Generate: python -c "import base64, os; print(base64.b64encode(os.urandom(32)).decode())"
AUDIT_SECRET_KEY_B64=dGhpcyBpcyBhIDMyLWJ5dGUgc2VjcmV0IGtleSBmb3IgdGVzdGluZw==

# Logging
LOG_LEVEL=INFO                   # DEBUG, INFO, WARNING, ERROR

# AWS (LocalStack for development)
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
AWS_ENDPOINT_URL=http://localstack:4566
```

## Building the Image

### Build for Development

```bash
docker build -t nhid-clinical:dev .
```

### Build for Production

```bash
# Single-layer production build without source mount
docker build \
  --target production \
  -t nhid-clinical:prod .

# Scan for vulnerabilities (requires Grype or Trivy)
trivy image nhid-clinical:prod
```

### View Image Layers

```bash
docker history nhid-clinical:dev
```

## Running the Container

### Development (with source mount)

```bash
docker run -it \
  -p 8000:8000 \
  -v $(pwd):/app \
  -v audit-data:/data \
  -e DEPLOYMENT_MODE=development \
  -e AUDIT_STORE_PATH=/data/audit_events.db \
  nhid-clinical:dev
```

### Production (no source mount)

```bash
docker run -d \
  -p 8000:8000 \
  -v audit-data:/data \
  -e DEPLOYMENT_MODE=production \
  -e AUDIT_STORE_PATH=/data/audit_events.db \
  -e AUDIT_SECRET_KEY_B64=$AUDIT_SECRET_KEY \
  --restart unless-stopped \
  --health-cmd='curl -f http://localhost:8000/health' \
  --health-interval=30s \
  --health-timeout=10s \
  --health-retries=3 \
  nhid-clinical:prod
```

## Health Checks

### Local Endpoint

```bash
curl http://localhost:8000/health
```

### Expected Response

```json
{
  "status": "healthy",
  "audit_store": "connected",
  "audit_store_latency_ms": 2.5,
  "timestamp": "2026-07-31T12:34:56Z"
}
```

### Docker Health Status

```bash
docker ps --filter "name=nhid-api"
```

Look for `healthy` in the STATUS column.

## Persistence and Data

### Audit Events Database

The SQLite audit database is persisted in the `audit-data` volume:

```bash
# View volume location
docker volume inspect nhid_audit-data

# Backup database
docker cp nhid-clinical-api:/data/audit_events.db ./audit_events_backup.db

# Restore database
docker cp ./audit_events_backup.db nhid-clinical-api:/data/audit_events.db
```

### LocalStack Data

LocalStack data is ephemeral by default but can be persisted:

```env
# In docker-compose.yml, modify localstack volumes:
volumes:
  - localstack-data:/tmp/localstack
```

## Logging

### View Logs

```bash
# Using docker-compose
docker-compose logs -f nhid-api

# Using docker
docker logs -f nhid-clinical-api
```

### Log Levels

Set `LOG_LEVEL` environment variable:
- `DEBUG`: Detailed diagnostic information (noisy)
- `INFO`: General informational messages (default)
- `WARNING`: Warning messages only
- `ERROR`: Errors only

## Security Considerations

### Non-Root User

The image runs as user `nhid` (UID 1000) for security:

```dockerfile
RUN useradd -m -u 1000 nhid && chown -R nhid:nhid /app /data
USER nhid
```

### Secret Key Management

Never commit the `AUDIT_SECRET_KEY_B64` value to version control:

1. Generate locally for development:
   ```bash
   python -c "import base64, os; print(base64.b64encode(os.urandom(32)).decode())"
   ```

2. Set via environment variable:
   ```bash
   export AUDIT_SECRET_KEY_B64=$(python -c "import base64, os; print(base64.b64encode(os.urandom(32)).decode())")
   docker-compose up
   ```

3. For production, use AWS Secrets Manager:
   ```bash
   aws secretsmanager create-secret --name nhid/audit-secret-key --secret-string "$AUDIT_SECRET_KEY_B64"
   ```

### Network Isolation

The docker-compose configuration creates an isolated network (`nhid-network`):

```yaml
networks:
  nhid-network:
    driver: bridge
```

Only services on this network can communicate; external access is via published ports only (8000, 4566).

## Deployment Variations

### Development Stack

```bash
# Full stack with source code reload
docker-compose up

# Services: nhid-api + localstack
# Volumes: source code mounted, audit data persisted
# Network: bridges between services
```

### Staging (Pre-Production Test)

```bash
# Build without source mount
docker build -t nhid-clinical:staging .

# Run with production secrets from AWS
docker run -d \
  -e DEPLOYMENT_MODE=staging \
  -e AUDIT_SECRET_KEY_B64=$(aws secretsmanager get-secret-value --secret-id nhid/audit-secret-key --query SecretString --output text) \
  nhid-clinical:staging
```

### Production (AWS ECS/Fargate)

```bash
# Push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com
docker tag nhid-clinical:prod <account-id>.dkr.ecr.us-east-1.amazonaws.com/nhid-clinical:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/nhid-clinical:latest

# Deploy via ECS task definition (see docs/DEPLOYMENT-SECURITY-CHECKLIST.md)
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker logs nhid-clinical-api

# Check if port 8000 is already in use
lsof -i :8000

# Try different port
docker-compose run -p 8001:8000 nhid-api
```

### Health Check Fails

```bash
# Test health endpoint manually
docker exec nhid-clinical-api curl -v http://localhost:8000/health

# Check database connectivity
docker exec nhid-clinical-api ls -la /data/

# Check permissions
docker exec nhid-clinical-api id
```

### LocalStack Not Ready

```bash
# Logs may show connection refused initially; LocalStack takes ~30s to start
docker logs nhid-localstack

# Wait for "Ready" message in logs
docker logs nhid-localstack | grep Ready
```

### Database Locked (SQLite)

```bash
# Remove stale database file
docker exec nhid-clinical-api rm -f /data/audit_events.db

# Restart container
docker-compose restart nhid-api
```

## Testing

### Unit Tests (No Docker)

```bash
pytest tests/ -v
```

### Docker Smoke Tests

```bash
# Validates Dockerfile syntax, docker-compose.yml structure, volume configuration
pytest tests/test_docker_smoke.py -v
```

### Integration Tests (With Docker)

```bash
# Start services
docker-compose up -d

# Wait for health check
sleep 10

# Run conformance tests against live container
pytest tests/test_vapi_adapter.py::TestLiveConformanceEndpoint -v

# Cleanup
docker-compose down
```

### E2E Test Script

```bash
#!/bin/bash
set -e

echo "Starting NHID-Clinical Docker stack..."
docker-compose up -d --wait

echo "Running health check..."
curl -f http://localhost:8000/health

echo "Running conformance tests..."
curl -X POST http://localhost:8000/v1/adapters/vapi/check \
  -H "Content-Type: application/json" \
  -d @tests/demo_scenarios/vapi_noncompliant.json | jq '.conformant'

echo "Cleaning up..."
docker-compose down -v
```

## Performance Tuning

### Resource Limits (docker-compose)

```yaml
services:
  nhid-api:
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
```

### Database Optimization

```bash
# Enable WAL (write-ahead logging) for better concurrency:
docker exec nhid-clinical-api sqlite3 /data/audit_events.db "PRAGMA journal_mode=WAL;"

# Check pragma settings:
docker exec nhid-clinical-api sqlite3 /data/audit_events.db ".headers on" "PRAGMA journal_mode;"
```

## Monitoring and Observability

### Metrics Endpoint (Future)

Once monitoring is added (Phase 6A Day 5):

```bash
curl http://localhost:8000/metrics
```

Expected Prometheus metrics:
- `audit_events_total` - Total events written
- `audit_verification_failures` - Chain verification failures
- `audit_store_latency_ms` - Database latency

### Logs to CloudWatch (Production)

See `docs/DEPLOYMENT-SECURITY-CHECKLIST.md` for CloudWatch log group setup.

## References

- [Docker Multi-Stage Builds](https://docs.docker.com/build/building/multi-stage/)
- [Docker Compose Networking](https://docs.docker.com/compose/networking/)
- [LocalStack Documentation](https://docs.localstack.cloud/)
- [Python 3.13 Slim Image](https://hub.docker.com/_/python)
- [Security Best Practices](https://docs.docker.com/engine/security/)
