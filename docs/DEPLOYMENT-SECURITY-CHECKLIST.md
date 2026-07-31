# Deployment Security Checklist: NHID-Clinical

This checklist ensures NHID-Clinical is deployed securely across development, staging, and production environments.

## Pre-Deployment

### Code Review
- [ ] Security.md and this checklist reviewed by team
- [ ] No hardcoded secrets in config files
- [ ] No credentials in git history (run `git log --all -p -- .env`)
- [ ] Dependencies scanned for vulnerabilities (`pip audit` or `safety check`)
- [ ] No debug logging in production code paths
- [ ] Input validation on all API endpoints (PolicyEngine)
- [ ] Error messages don't leak system information

### Configuration Review
- [ ] AUDIT_SECRET_KEY_B64 generated with `os.urandom(32)` (cryptographically secure)
- [ ] AUDIT_SECRET_KEY_B64 stored in AWS Secrets Manager (production only)
- [ ] DEPLOYMENT_MODE set to "production" (not development/staging)
- [ ] LOG_LEVEL set to "INFO" (DEBUG denied by config validation)
- [ ] AUDIT_STORE_PATH points to encrypted filesystem
- [ ] AWS_ENDPOINT_URL not set (uses real AWS, not LocalStack)
- [ ] AWS credentials in IAM roles (not hardcoded)
- [ ] All required environment variables documented in .env.example

### Infrastructure Review
- [ ] Docker image passes security scanning (`trivy image nhid-clinical:prod`)
  - No critical vulnerabilities
  - Base image is latest Python 3.13-slim
  - No secrets in Docker layers
- [ ] Dockerfile uses multi-stage build (no build tools in production)
- [ ] Dockerfile runs as non-root user (nhid:1000)
- [ ] SQLite database file on encrypted volume
- [ ] Database directory has restricted permissions (0755)
- [ ] Database file has restricted permissions (0644)
- [ ] Network isolation: no public S3 buckets
- [ ] VPC: Lambda in private subnet (NAT for outbound only)
- [ ] Security Groups:
  - [ ] Lambda: ingress from API Gateway only
  - [ ] RDS (if used): ingress from Lambda only, not internet
  - [ ] Database: no ingress from internet

### Secrets Management
- [ ] Secret key created and stored in AWS Secrets Manager
  ```bash
  aws secretsmanager create-secret \
    --name nhid/audit-secret-key \
    --secret-string "$(python -c 'import base64, os; print(base64.b64encode(os.urandom(32)).decode())')"
  ```
- [ ] Lambda IAM role has permission to read secret:
  ```json
  {
    "Effect": "Allow",
    "Action": ["secretsmanager:GetSecretValue"],
    "Resource": "arn:aws:secretsmanager:region:account:secret:nhid/*"
  }
  ```
- [ ] Secrets Manager secret tags applied (`Environment=production`)
- [ ] Secret rotation enabled (90-day default) — Phase 6B
- [ ] No secret history in CloudWatch Logs

## Deployment

### Pre-Flight Checks
- [ ] Backup existing database before deployment
  ```bash
  aws s3 cp s3://nhid-backups/audit_events.db ./audit_events_backup_$(date +%s).db
  ```
- [ ] Test deployment in staging first (not direct to production)
- [ ] Verify staging events sign and verify correctly
- [ ] Staging database can be deleted without risk
- [ ] Production database is separate from staging

### Infrastructure Deployment
- [ ] CloudFormation/SAM template reviewed
- [ ] Lambda function uses latest code (verified by git commit SHA)
- [ ] Lambda timeout set appropriately (not too short for large queries)
- [ ] Lambda memory sufficient for event processing (512MB minimum)
- [ ] Environment variables passed via Lambda configuration (not code)
- [ ] CloudWatch Log Group created:
  ```bash
  aws logs create-log-group --log-group-name /nhid-clinical/audit
  aws logs put-retention-policy --log-group-name /nhid-clinical/audit --retention-in-days 90
  ```
- [ ] X-Ray tracing enabled for performance monitoring
- [ ] DLQ (Dead Letter Queue) configured for failed events

### Secrets Deployment
- [ ] AUDIT_SECRET_KEY_B64 retrieved from Secrets Manager
  ```bash
  SECRET=$(aws secretsmanager get-secret-value --secret-id nhid/audit-secret-key --query SecretString --output text)
  aws lambda update-function-configuration \
    --function-name nhid-conformance-check \
    --environment "Variables={AUDIT_SECRET_KEY_B64=$SECRET,DEPLOYMENT_MODE=production}"
  ```
- [ ] Verify Lambda environment variables do NOT print secret in logs
- [ ] CloudWatch Logs filter prevents secret logging:
  ```bash
  aws logs create-metric-filter \
    --log-group-name /aws/lambda/nhid-conformance-check \
    --filter-pattern "[...secret_key...]" \
    --metric-transformations metricName=SecretInLogs,metricValue=1
  ```

### Verification Checks
- [ ] Lambda can assume role with Secrets Manager access
  ```bash
  aws lambda invoke \
    --function-name nhid-conformance-check \
    --payload '{"test": true}' \
    response.json
  cat response.json  # Should not error with "access denied"
  ```
- [ ] API Gateway authorizer working (API key or OAuth)
- [ ] TLS certificate valid (minimum TLS 1.2)
- [ ] API Gateway WAF rules applied (if available)
- [ ] CloudWatch alarms created:
  - [ ] Lambda errors (ErrorCount > 0)
  - [ ] Lambda throttles (Throttles > 0)
  - [ ] Signature verification failures (metric from custom logs)
  - [ ] Database latency spikes (Duration > 500ms)

### Logging Setup
- [ ] CloudWatch Log Group retention set to 90 days
- [ ] Log data encrypted at rest (default in AWS)
- [ ] Log access restricted to security team
  ```bash
  aws logs put-resource-policy \
    --policy-name "RestrictLogAccess" \
    --policy-text '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"AWS":"arn:aws:iam::ACCOUNT:role/SecurityTeam"},"Action":"logs:*","Resource":"*"}]}'
  ```
- [ ] CloudWatch Logs Insights queries configured:
  ```
  fields @timestamp, event_id, violations
  | filter violations like /critical/
  | stats count() as critical_violations by event_type
  ```

## Post-Deployment

### Validation
- [ ] Test endpoint returns expected response
  ```bash
  ENDPOINT=$(aws cloudformation describe-stacks --stack-name nhid-clinical-api --query 'Stacks[0].Outputs[?OutputKey==ConformanceEndpoint].OutputValue' --output text)
  KEY=$(aws apigateway get-api-key --api-key-id <key-id> --include-value --query value --output text)
  
  curl -X POST $ENDPOINT \
    -H "x-api-key: $KEY" \
    -H "Content-Type: application/json" \
    -d @tests/sample_request.json
  ```
- [ ] Response contains `conformant`, `action`, `violations` fields
- [ ] Verify chain succeeds on stored events
  ```bash
  python -c "
  from src.audit_store import AuditStore
  store = AuditStore(db_path='/data/audit_events.db')
  is_valid, error = store.verify_chain('session-xyz')
  assert is_valid, f'Chain verification failed: {error}'
  print('✓ Audit chain verified successfully')
  "
  ```
- [ ] No errors in CloudWatch Logs (grep for ERROR, CRITICAL)

### Monitoring Setup
- [ ] CloudWatch Dashboard created with metrics:
  - [ ] Lambda Invocations (RequestCount)
  - [ ] Lambda Errors (ErrorCount)
  - [ ] Lambda Duration (Average, P99)
  - [ ] Audit Events Written (custom metric)
  - [ ] Verification Failures (custom metric)
- [ ] SNS Topic for alerts created
- [ ] PagerDuty/Slack integration for critical alerts
- [ ] Weekly audit trail health report configured

### Documentation
- [ ] Runbook for emergency key rotation (Phase 6B)
- [ ] Runbook for database recovery
- [ ] Contact list updated (on-call engineer, security team, management)
- [ ] Incident response plan reviewed
- [ ] Backup and restore procedures tested

## Ongoing Operations

### Daily Checks
- [ ] CloudWatch Dashboard shows no errors or spikes
- [ ] Log volume is as expected (no sudden increases)
- [ ] No unauthorized API calls (403/401 errors < 1%)

### Weekly Checks
- [ ] Security patches available for base image?
  ```bash
  docker pull python:3.13-slim
  trivy image python:3.13-slim  # Check for CVEs
  ```
- [ ] Dependencies have security updates?
  ```bash
  pip list --outdated | grep -i security
  pip-audit  # Check for known vulnerabilities
  ```
- [ ] Audit trail verification: sample 10 random sessions and verify chains
- [ ] Database size reasonable? (check for runaway retention)

### Monthly Checks
- [ ] Security logs review (CloudTrail, VPC Flow Logs)
- [ ] IAM policy audit (least privilege)
- [ ] API usage patterns (detect anomalies)
- [ ] Backup integrity test (restore to staging, verify)
- [ ] Disaster recovery drill (simulate failure)

### Quarterly Checks
- [ ] Security audit (penetration testing — Phase 6B)
- [ ] Compliance audit (HIPAA/HITRUST — Phase 6B)
- [ ] Access review (who has Secrets Manager access?)
- [ ] Secret rotation (Phase 6B: rotate keys on schedule)
- [ ] Update this checklist based on lessons learned

## Rollback Procedure

If deployment fails or serious issue discovered:

1. **Stop Lambda invocations**:
   ```bash
   aws lambda update-function-configuration \
     --function-name nhid-conformance-check \
     --environment "Variables={DEPLOYMENT_MODE=maintenance}"
   ```

2. **Restore previous version**:
   ```bash
   aws lambda update-function-code \
     --function-name nhid-conformance-check \
     --s3-bucket nhid-lambda-code \
     --s3-key nhid-conformance-check-previous.zip
   ```

3. **Restore database backup**:
   ```bash
   aws s3 cp s3://nhid-backups/audit_events.db_pre_deployment /data/audit_events.db
   ```

4. **Notify team** and investigate root cause

5. **Test in staging** before redeployment

## Security Incident Response

### Signature Verification Failure
**Alert**: CloudWatch metric `VerificationFailures` > 0

**Response**:
1. [ ] Check CloudWatch Logs for specific failures
2. [ ] Verify database integrity: `sqlite3 /data/audit_events.db "PRAGMA integrity_check;"`
3. [ ] Check if secret key was rotated (phase 6B)
4. [ ] Query suspicious events:
   ```sql
   SELECT event_id, timestamp, verification_status FROM audit_events
   WHERE verification_status = 'FAILED' ORDER BY timestamp DESC LIMIT 10;
   ```
5. [ ] Engage security team if tampering suspected

### Unauthorized API Access
**Alert**: CloudWatch metric `UnauthorizedRequests` > threshold

**Response**:
1. [ ] Check API Gateway access logs
2. [ ] Identify source IP and user agent
3. [ ] Adjust WAF rules if pattern detected
4. [ ] Review API key usage
5. [ ] Consider rate limiting (Phase 6B)

### Database Corruption
**Alert**: CloudWatch metric `DatabaseErrors` > 0

**Response**:
1. [ ] Restore from backup
2. [ ] Run integrity check on backup
3. [ ] Re-verify audit chains
4. [ ] Audit access logs during corruption window
5. [ ] Report to compliance/legal if data loss

## Approval Sign-Off

Before production deployment, obtain written approval from:

- [ ] **Engineering Lead**: Code review and configuration
- [ ] **Security Lead**: Security architecture and checklist completion
- [ ] **Operations Lead**: Infrastructure and monitoring readiness
- [ ] **Compliance Officer**: Regulatory and audit trail requirements (if applicable)

---

**Deployment Date**: ___________

**Deployed By**: ___________

**Approved By**: ___________

**Version**: 1.0 (Phase 6A Day 4)
