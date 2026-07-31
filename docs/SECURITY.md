# Security: NHID-Clinical Audit Trail Framework

This document describes the security architecture, threat model, and mitigations for the NHID-Clinical audit trail system (ATR-01).

## Security Architecture

### 1. Cryptographic Integrity (ATR-01)

#### Design
- **Algorithm**: HMAC-SHA256 with 32-byte secret key
- **Canonical Form**: JSON representation with sorted keys and no whitespace
- **Chain Linking**: Previous event ID included in signature (detects tampering at any point in chain)
- **Constant-Time Comparison**: `hmac.compare_digest()` prevents timing attacks

#### Implementation
```python
# Canonical form: {"event_id": "...", "timestamp": "...", "event_type": "...", 
#                   "payload": {...}, "previous_event_id": "..."}
# HMAC-SHA256 with secret_key
# Returns: hex digest (64 chars)

# Verification: recompute hash, compare with stored hash
# Failure modes:
#   - Payload tampered → hash mismatch
#   - Timestamp changed → hash mismatch
#   - Event order changed (previous_event_id changed) → hash mismatch
#   - Signature replaced → hash mismatch
```

#### Threat Coverage
- **Payload Tampering**: Detected (payload change invalidates hash)
- **Timestamp Manipulation**: Detected (timestamp part of signed payload)
- **Chain Reordering**: Detected (previous_event_id change invalidates hash)
- **Signature Forgery**: Infeasible (HMAC requires secret key)
- **Dropped Events**: Detected by chain verification (missing link)

### 2. Persistent Storage (SQLite Backend)

#### Design
- **Storage**: SQLite database with ACID compliance
- **Schema**: Three tables (audit_events, audit_sessions, verification_records)
- **Access Control**: File system permissions (0644 for DB file, 0755 for directory)
- **Retention**: Per-event TTL with automatic cleanup

#### Implementation
```python
# Database path: /data/audit_events.db (in Docker)
# 
# audit_events table:
#   - event_id: UNIQUE NOT NULL (prevents duplicate writes)
#   - evidence_hash: Immutable signature
#   - expires_at: Automatic deletion after retention_days
#   - created_at: Timestamp set by database (not user-input)
#
# audit_sessions table:
#   - session_id: UNIQUE NOT NULL
#   - event_count: Auto-incremented on write
#   - closed_at: Mark session end
#
# verification_records table:
#   - Audit trail of verification checks (immutable history)
```

#### Threat Coverage
- **Write Once**: Unique constraint on event_id prevents overwrites
- **Deletion**: TTL-based automatic cleanup (configurable retention_days)
- **Corruption**: SQLite ACID compliance; journal mode provides crash recovery
- **Unauthorized Access**: File system ACL enforces read/write restrictions
- **Data Exposure**: SQLite file must be on encrypted filesystem in production

### 3. Secret Key Management

#### Key Properties
- **Size**: Exactly 32 bytes (256 bits)
- **Source**: 
  - Development: Auto-generated with `os.urandom(32)` (ephemeral)
  - Production: Must be provided via `AUDIT_SECRET_KEY_B64` environment variable
- **Storage**: 
  - Never committed to version control
  - Environment variable or AWS Secrets Manager (production)
  - Base64-encoded for safe transport

#### Key Derivation
```bash
# Generate new key (one-time operation)
python -c "import base64, os; print(base64.b64encode(os.urandom(32)).decode())"

# Output: dGhpcyBpcyBhIDMyLWJ5dGUgc2VjcmV0IGtleSBmb3IgdGVzdGluZw==

# Encode for environment variable
export AUDIT_SECRET_KEY_B64=$(python -c "import base64, os; print(base64.b64encode(os.urandom(32)).decode())")

# Production: Store in AWS Secrets Manager
aws secretsmanager create-secret \
  --name nhid/audit-secret-key \
  --secret-string "$AUDIT_SECRET_KEY_B64"
```

#### Threat Coverage
- **Key Compromise**: Invalidates all signatures (requires re-signing events)
- **Weak Random**: Mitigated by OS-level `os.urandom()` (uses /dev/urandom)
- **Hardcoded Key**: Prevented by failing if `AUDIT_SECRET_KEY_B64` not set in production
- **Key Leakage**: Environment variables may be logged; use Secrets Manager in production

### 4. Deployment Mode Enforcement

#### Modes
```
Development:
  - DEBUG logging enabled
  - Auto-generated secret key (ephemeral)
  - Hot reload and live debugging allowed
  - SQLite path validation: none

Staging:
  - INFO logging (no DEBUG)
  - Requires explicit AUDIT_SECRET_KEY_B64
  - Full production validation
  - Pre-deployment testing environment

Production:
  - INFO logging (DEBUG denied at config validation)
  - Requires AUDIT_SECRET_KEY_B64 (fails if missing)
  - Requires SQLite path writable (validation at startup)
  - No debug output, no hot reload
  - Uses AWS Secrets Manager for key management
```

#### Threat Coverage
- **Accidental Debug Mode**: Config validation prevents DEBUG in production
- **Missing Secrets**: Startup validation fails immediately
- **Path Misconfiguration**: Writable directory check at startup

## Threat Model

### Assets
1. **Audit Events**: Immutable records of decisions and policy violations
2. **Timestamps**: Proof of when events occurred
3. **Chain Integrity**: Proof that no events were dropped or reordered
4. **Secret Key**: Ability to sign new events

### Threats

| Threat | Attack Scenario | Severity | Mitigation |
|--------|-----------------|----------|-----------|
| **Payload Tampering** | Attacker modifies event (e.g., changes violation type) | Critical | HMAC signature; verify_chain() detects |
| **Timestamp Manipulation** | Attacker changes event timestamp to hide sequence | Critical | Timestamp part of signed payload; DB created_at immutable |
| **Chain Reordering** | Attacker drops/reorders events to hide violations | Critical | previous_event_id in signature; verify_chain() detects |
| **Signature Forgery** | Attacker creates fake event with forged signature | Critical | 32-byte secret key; HMAC infeasible to forge |
| **Key Compromise** | Attacker obtains secret key, signs fake events | Critical | Secrets Manager in production; key rotation plan (Phase 6B) |
| **Unauthorized Write** | Attacker bypasses code and writes directly to database | High | Event ID uniqueness constraint; API layer validation |
| **Unauthorized Read** | Attacker reads audit database | High | File system ACL; encryption at rest (Phase 6B) |
| **Deletion** | Attacker deletes events to hide violations | Medium | TTL-based retention; cannot delete before expiry |
| **DoS: Event Spam** | Attacker writes unlimited events to consume storage | Medium | Rate limiting (Phase 6B); storage quotas |
| **Dropped Events** | Network failure during write | Low | Retry logic; transaction rollback (handled by SQLite) |
| **Unrelated Vulnerabilities** | XSS, SQL injection in other components | Medium | API layer validates input; parametrized queries |

### Attack Surfaces

#### External
1. **HTTP API** (`/v1/adapters/vapi/check`)
   - Input validation required (PolicyEngine already implemented)
   - Rate limiting needed (Phase 6B)
   - TLS/HTTPS required in production

2. **Lambda Handler** (`functions/handler.py`)
   - Deployed via AWS Lambda (IAM authorization)
   - API Gateway protects with API key
   - CloudWatch logs capture all invocations

#### Internal
1. **File System** (`/data/audit_events.db`)
   - Readable by: nhid user (UID 1000) in Docker
   - Writable by: nhid user only
   - Permission bits: 0644 for file, 0755 for directory

2. **Memory**
   - Secret key held in process memory
   - No secrets logged (structured logging with redaction)
   - Python process runs as non-root (Docker)

3. **Docker Container**
   - Non-root user (nhid:1000) prevents privilege escalation
   - Read-only filesystem for code (except /data volume)
   - Network isolation via docker-compose bridge

## Security Best Practices

### Key Management
✅ **DO**:
- Generate keys with `os.urandom()` (cryptographically secure)
- Store in environment variables for development
- Store in AWS Secrets Manager for production
- Rotate keys periodically (Phase 6B implementation)
- Audit key usage via CloudWatch Logs

❌ **DON'T**:
- Hardcode keys in code or config files
- Use weak RNG (e.g., `random.random()`)
- Commit `.env` files with real keys
- Share keys via email or Slack
- Use same key across environments

### Audit Events
✅ **DO**:
- Include all relevant context (agent ID, org ID, timestamp)
- Use immutable timestamps (ISO 8601 UTC)
- Sign before writing to database
- Verify chain on retrieval (production audit queries)
- Archive events after retention period

❌ **DON'T**:
- Allow event editing after creation
- Use local time (without timezone)
- Skip signature verification
- Store PII in audit payloads (use hash references)
- Rely on single signature (use chain verification)

### Deployment
✅ **DO**:
- Require `AUDIT_SECRET_KEY_B64` in production
- Validate configuration at startup
- Encrypt filesystem in production
- Use HTTPS for API (API Gateway handles)
- Restrict database file permissions (0644)
- Run as non-root user (Docker nhid:1000)
- Monitor CloudWatch logs for tampering attempts

❌ **DON'T**:
- Disable signature verification
- Use development secret key in production
- Allow DEBUG logging in production
- Expose database file via HTTP
- Allow write access from untrusted networks
- Run as root (privilege escalation risk)

## Security Testing

### Unit Tests
- ✅ Signature verification with correct key
- ✅ Signature failure with tampered payload
- ✅ Signature failure with changed timestamp
- ✅ Chain verification success (valid chain)
- ✅ Chain verification failure (tampering detected)
- ✅ Chain verification failure (broken link detected)
- ✅ Key size validation (reject < 32 or > 32 bytes)

### Integration Tests
- ✅ End-to-end event creation and verification
- ✅ Multiple events in sequence (chain)
- ✅ Database persistence and retrieval
- ✅ Concurrent event writes (SQLite handles)

### Production Validation
- ✅ Configuration validation (Secrets Manager key present)
- ✅ Database directory writable at startup
- ✅ Logging doesn't expose secrets
- ✅ API Gateway enforces HTTPS

### Future Testing (Phase 6B)
- Cryptanalysis (independent audit of HMAC usage)
- Penetration testing (external security firm)
- Key rotation testing
- Large-scale performance testing (1M+ events)
- Disaster recovery testing

## Incident Response

### Suspected Tampering
**Detection**: `verify_chain()` returns `(False, error_message)`

**Response**:
1. Trigger alert in CloudWatch
2. Lock database (read-only mode)
3. Notify security team
4. Extract events before tampering point
5. Rotate secret key (Phase 6B: key versioning)
6. Re-validate entire audit trail with new key

### Key Compromise
**Detection**: Unauthorized signature creation detected

**Response**:
1. Revoke compromised key immediately
2. Issue new key via Secrets Manager
3. Re-sign all events with new key (Phase 6B)
4. Audit who accessed the compromised key
5. Update Lambda environment to use new key

### Database Corruption
**Detection**: SQLite integrity check fails

**Response**:
1. Restore from backup (daily snapshots)
2. Re-verify chain from backup
3. Audit loss period (which events were lost)
4. Implement incremental backups (Phase 6B)

## Compliance

### Standards Alignment
- **HMAC-SHA256**: FIPS 140-2 approved algorithm
- **Write-Once Storage**: WORM compliance (immutable records)
- **Signature Verification**: Non-repudiation (proof of intent)
- **Timestamp Immutability**: Forensic timeline validity

### Audit Trail Requirements
- ✅ Immutable event records
- ✅ Cryptographic signatures
- ✅ Chronological ordering
- ✅ Event correlation (session_id links)
- ✅ Retention policies
- ✅ Tampering detection

### Future Compliance (Phase 6B)
- HIPAA Business Associate Agreement (BAA)
- HITRUST CSF certification
- SOC 2 Type II audit
- 21 CFR Part 11 (FDA) compliance

## References

- [OWASP: Authentication](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [NIST: Cryptographic Algorithms](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-38D.pdf)
- [RFC 2104: HMAC](https://datatracker.ietf.org/doc/html/rfc2104)
- [SQLite: Security](https://www.sqlite.org/security.html)
- [AWS: Secrets Manager](https://docs.aws.amazon.com/secretsmanager/)
