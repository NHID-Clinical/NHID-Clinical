# NHID-Clinical — Full Project Specification

**Author:** Brianna Baynard (bnbaynard@gmail.com)
**License:** CC BY 4.0
**Status:** v1.4 on main — 95 unit tests passing, 18 integration skipped (no server)
**Repo:** thankcheeses/NHID-Clinical
**Site:** nhid-clinical.org
**Last updated:** 2026-06-02

---

## What This Is

NHID-Clinical is an open-source governance reference implementation and voluntary
compliance standard for AI voice agents operating in B2B healthcare payer-provider
calls. It defines what an AI agent MUST do to be considered safe and compliant:
disclose its identity, protect PHI, honor escalation requests, log every interaction,
and prevent impersonation.

**The problem it solves:** AI agents calling health insurance companies on behalf of
providers (checking eligibility, submitting prior auths, following up on claims) have
no governance layer. NHID-Clinical is that layer — a deterministic policy engine that
any AI product can embed to enforce the rules on every call.

**The moat:** Not the code (it's open). The moat is being the submitted NIST standard,
having a published conformance test suite, and being the existing reference that vendors
cite. Timing and credibility, not secrecy. Anyone can self-host; they just won't have
the verified credential.

---

## Current State (as of 2026-06-02)

- **`main`**: v1.4, **95 passed, 18 skipped** — fully merged and stable
- **`claude/code-review-fixes-98Ir1`**: active working branch, also at 95/18
- **`claude/perf-fix-98Ir1`**: open PR → main with Windows timing fix for performance test
- **`feature/v1.4-auth`**: superseded, now merged into main via PR #212

**Test breakdown on any current branch:**
```
113 collected total
  20 passed  — failure_injection_harness.py (TestPolicyEngineUnit, pure unit tests)
  18 skipped — failure_injection_harness.py (require live server at :8000)
  25 passed  — test_identity.py
  70 passed  — test_voice_policy.py
─────────────────
  95 passed, 18 skipped
```

---

## Repository Layout

```
NHID-Clinical/
├── src/
│   ├── nhid_policy_engine_v1.py     # Core NHID v1.3 rules (IDG-01 … ATR-01 + bot-to-bot)
│   ├── voice_policy.py              # Voice-optimized rule engine + PHI gate
│   └── agent_identity.py            # v1.4 Ed25519 cryptographic identity layer
├── tests/
│   ├── test_voice_policy.py         # 70 unit tests for voice_policy.py
│   ├── test_identity.py             # 25 unit tests for agent_identity.py
│   ├── failure_injection_harness.py # 38 tests: 20 pure unit + 18 skip (need server)
│   └── trace_generator.py           # Generates synthetic audit traces
├── main.py                          # FastAPI app: wires all routers + badge endpoint
├── nhid_api_endpoints.py            # /v1/policy/evaluate, /v1/compliance/states
├── nhid_attest.py                   # /v1/attest — JWT delegation tokens (SQLite)
├── nhid_payer.py                    # /v1/payer/screen — inbound call screening
├── nhid_audit_export.py             # /v1/audit/log, /v1/audit/export
├── schema/
│   └── nhid_trace_schema_v1.json    # JSON schema for audit trace events
├── conformance/
│   └── nhid_conformance_test_suite_v1.yaml  # YAML conformance test spec (NIST artifact)
├── scripts/
│   └── validate_ci.py               # CI invariant enforcer (UNIT_EXPECTED = 95)
├── examples/
│   └── issue_and_verify.py          # v1.4 end-to-end Ed25519 demo
├── .github/workflows/
│   ├── ci.yml                       # Unit invariant gate
│   └── nhid-gates.yml               # Production readiness gates (5 jobs + release gate)
├── PROJECT_SPEC.md                  # This file
├── CHANGELOG_v1.4.md                # v1.4 technical changelog
├── requirements.txt
└── pytest.ini
```

---

## Python Dependencies

```
fastapi>=0.110.0
httpx>=0.27.0
pytest>=8.0.0
pytest-asyncio>=0.23.0
pydantic>=2.6.0
uvicorn>=0.29.0
python-multipart>=0.0.9
pyyaml>=6.0.1
jsonschema>=4.21.0
cryptography>=41.0.0
PyJWT>=2.8.0
```

Install: `pip install -r requirements.txt`
Run: `uvicorn main:app --reload`

---

## Module: `src/nhid_policy_engine_v1.py` — Core Policy Engine

**NHID spec version:** 1.3
**Design contract:** Pure functions only. No I/O, no network, no LLM calls.
Every function returns a `PolicyDecision`. Never raises.

### Data Structures

```python
@dataclass(frozen=True)
class BoundaryViolation:
    rule_id: str                    # e.g. "IDG-01"
    description: str
    severity: ViolationSeverity     # CRITICAL | MAJOR | MINOR

@dataclass
class PolicyDecision:
    action: PolicyAction            # DISCLOSE_IDENTITY | ESCALATE_HUMAN | CONTINUE_AI | DENY_DATA | LOG_ONLY
    reason_code: str                # e.g. "IDG01_DISCLOSURE_MISSING"
    policy_version: str             # POLICY_ENGINE_VERSION = "1.0.0"
    violations: list[BoundaryViolation]
    next_state: str                 # state machine output e.g. "AWAITING_DISCLOSURE"
    twiml_fallback: str | None      # ready-to-use TwiML string if needed
    gather_speech: bool
```

### The Five Rules + Bot-to-Bot Supplement

**IDG-01 — Identity Disclosure Gate**
The AI MUST proactively disclose its non-human identity at the start of every
interaction before any operational data exchange.
- Input: `healthcare_governance.disclosure_timestamp`, `healthcare_governance.identity_assertion_text`, `session.turn_count`, `counterparty_type`
- Pass: `disclosure_timestamp` set AND `identity_assertion_text` non-empty → `CONTINUE_AI / IDG01_DISCLOSURE_CONFIRMED`
- Fail (no timestamp): `DISCLOSE_IDENTITY / IDG01_DISCLOSURE_MISSING` + TwiML "I am an automated system"
- Fail (empty text): `CONTINUE_AI / IDG01_ASSERTION_TEXT_MISSING` (MAJOR violation)
- Bot-to-bot: stricter gate when `counterparty_type == "ai_agent"`

**PDX-01 — Pre-Data Exchange Gate**
The AI MUST NOT request or accept PHI before identity disclosure is confirmed.
- PHI trigger fields: `member_id`, `npi`, `date_of_birth`, `claim_number`, `prior_auth_number`, `diagnosis_code`, `procedure_code`, `provider_tin`
- PHI speech patterns: "member id", "date of birth", "dob", "claim number", "prior auth", "authorization number", "diagnosis", "procedure code", "icd", "tax id", "tin"
- Fail: PHI attempted before disclosure → `DENY_DATA / PDX01_PHI_GATE_TRIGGERED`
- Pass: disclosure done + PHI → `CONTINUE_AI / PDX01_GATE_CLEARED`
- Pass: no PHI → `CONTINUE_AI / PDX01_NO_PHI_REQUESTED`

**DBC-01 — Deceptive Behavior Check**
The AI MUST NOT use deceptive audio artifacts or claim human/licensed-professional status.
- Input: `healthcare_governance.deceptive_artifact_flags` list
- Fail: any flag present → `LOG_ONLY / DBC01_ARTIFACT_DETECTED` (CRITICAL per flag)
- Pass: no flags → `CONTINUE_AI / DBC01_NO_ARTIFACTS`

**EIT-01 — Escalation Implementation Test**
The AI MUST provide a functional path to a human operator when requested.
- Escalation triggers: "speak to a human", "talk to a person", "representative", "transfer me", "speak to someone", "real person", "human agent", "supervisor", "manager", "i need help", "can't help me", "not what i asked"
- Fail (no path): escalation requested + `session.escalation_path_available == False` → `ESCALATE_HUMAN / EIT01_NO_ESCALATION_PATH`
- Pass: escalation honored → `ESCALATE_HUMAN / EIT01_ESCALATION_TRIGGERED` + TwiML
- Pass: not requested → `CONTINUE_AI / EIT01_NO_ESCALATION_TRIGGER`

**ATR-01 — Audit Trail Requirements**
Every event MUST carry a complete, tamper-evident audit trail.
- Required top-level fields: `event_id`, `timestamp`, `session_id`, `request_id`, `event_type`, `actor_id`, `state_before`, `state_after`, `replay_mode`, `external_calls_cached`, `execution_context`
- Required in `execution_context`: `pipeline_version`, `policy_engine_version`, `nhid_schema_version`
- Fail: any field missing/null → `LOG_ONLY / ATR01_AUDIT_FIELDS_MISSING` (CRITICAL per field)
- Pass: all present → `CONTINUE_AI / ATR01_AUDIT_COMPLETE`

**Bot-to-Bot Supplement** (non-numbered, v1.3 extension)
When `counterparty_type == "ai_agent"`, both parties must disclose before data exchange.
- Fail: no `disclosure_timestamp` in bot-to-bot → `DENY_DATA / BOT2BOT_UNDISCLOSED_AGENT`
- Pass: disclosed → `CONTINUE_AI / BOT2BOT_BOTH_DISCLOSED`
- N/A: human counterparty → `CONTINUE_AI / BOT2BOT_NOT_APPLICABLE`

### Composite Evaluator

```python
decision = evaluate_all(session, event)
```

Runs all 5 rules + bot-to-bot. Action priority (most restrictive wins):
`DENY_DATA(5) > ESCALATE_HUMAN(4) > DISCLOSE_IDENTITY(3) > LOG_ONLY(2) > CONTINUE_AI(1)`
All violations from all rules are merged into a single list on the returned decision.

---

## Module: `src/voice_policy.py` — Voice Policy Engine

Optimized for real-time voice transcript evaluation. Supports a simple legacy API
and a full rule-based path with tenant-configurable rulesets.

### Key Constants

```python
POLICY_VERSION = "VOICE-POLICY-v1.0"

# Legacy default escalation phrases (used in non-ruleset path):
_ESCALATION_PHRASES = [
    "speak to a human", "real person", "agent please",
    "transfer me", "human agent", "talk to someone",
]

# IMMUTABLE — enforced even when ruleset is provided, cannot be disabled by tenant config:
_GLOBAL_SAFETY_PHRASES: tuple = (
    "speak to a human",
    "agent please",
    "real person",
)
```

**Critical behavior:** A tenant can configure a custom ruleset with an empty phrase list
or with the escalation rule disabled. The 3 phrases in `_GLOBAL_SAFETY_PHRASES` will STILL
trigger `"escalate"` — they are checked after all ruleset rules and cannot be suppressed.
The other 3 legacy phrases (`transfer me`, `human agent`, `talk to someone`) ARE suppressible
via ruleset config — they return `"allow"` if the rule is disabled or phrase list is empty.

### PHI State Machine

```python
class DisclosureState(str, Enum):
    AWAITING = "awaiting_disclosure_ack"
    CONFIRMED = "disclosure_confirmed"

def get_disclosure_state(session_state: dict) -> DisclosureState:
    # Returns CONFIRMED if session_state["disclosure_confirmed"] is truthy

def phi_gate(session_state: dict, phi_fields: dict | None) -> None:
    # Raises PermissionError if phi_fields is non-empty and disclosure not confirmed
    # Call before any PHI processing in the voice pipeline
```

### Public API

```python
result = run_voice_policy(
    transcript_text="speak to a human please",
    session_state={"disclosure_confirmed": True},
    phrases=None,           # (legacy) override escalation phrases; only used when ruleset=None
    policy_version=None,    # (legacy) version string to embed; defaults to POLICY_VERSION
    ruleset=None,           # (preferred) list of rule dicts; when provided uses rule-based path
    phi_fields=None,        # PHI gate input; raises PermissionError before disclosure
)
# result = {"action": "escalate", "reason_code": "HUMAN_ESCALATION_REQUESTED", "policy_version": "..."}
```

**Return action values:** `"disclose"` | `"escalate"` | `"allow"`

**Ruleset path:** rules evaluated in ascending `priority` order; disabled rules (`"enabled": False`)
skipped; global safety phrases checked last regardless of ruleset.

**Rule dict format:**
```python
{
    "rule_key": "HUMAN_ESCALATION_REQUESTED",   # or "REQUIRE_UPFRONT_DISCLOSURE"
    "rule_type": "phrase_match",                # or "builtin"
    "enabled": True,
    "priority": 10,
    "params": {"phrases": ["speak to a human", "agent please"]},
}
```

**Legacy path** (when `ruleset=None`): checks `check_disclosure()` first, then
`check_escalation()` with the `phrases` override or `_ESCALATION_PHRASES` default.

---

## Module: `src/agent_identity.py` — Cryptographic Identity Layer (v1.4)

Solves NPI impersonation: any AI can look up a real provider NPI from NPPES in seconds.
A valid passport requires a cryptographic signature from the provider's private key —
something public NPI data cannot produce.

**Status:** Library/reference code only. NOT wired to any HTTP endpoint.
The pilot uses `nhid_attest.py` (JWT over SQLite) for delegation. `agent_identity.py` is
the design target for v1.5+ when the cryptographic identity layer gets an HTTP API.

### Constants

```python
ERR_EXPIRED         = "ERR_EXPIRED"
ERR_REVOKED         = "ERR_REVOKED"
ERR_INVALID_SIG     = "ERR_INVALID_SIG"
ERR_NONCE_MISMATCH  = "ERR_NONCE_MISMATCH"
ERR_SCOPE_VIOLATION = "ERR_SCOPE_VIOLATION"
ERR_INVALID_NPI     = "ERR_INVALID_NPI"
ERR_CHAIN_NARROWING = "ERR_CHAIN_NARROWING"
ERR_CHAIN_TOO_LONG  = "ERR_CHAIN_TOO_LONG"
MAX_CHAIN_DEPTH     = 3
```

### Data Model

```python
@dataclass
class Delegation:
    provider_npi: str           # validated: exactly 10 digits (regex ^\d{10}$), or ""
    agent_id: str
    agent_public_key_b64: str   # Ed25519 public key, base64url-encoded (Raw format)
    scope: List[str]            # e.g. ["eligibility", "claim_status"]
    expires_at: int             # Unix timestamp
    created_at: int             # Unix timestamp
    delegation_id: str          # UUID4 — never deterministic, never replayable
    call_sid: str = ""          # Twilio call SID (optional, binds token to specific call)
    nonce: str = ""             # SHA-256(f"{call_sid}:{created_at}") if call_sid set

    def to_json(self) -> str:
        # MUST stay as: json.dumps(asdict(self), sort_keys=True, separators=(',',':'))
        # Changing this format breaks all existing signatures

@dataclass
class AgentPassport:
    delegation: Delegation
    signature_b64: str          # Provider's Ed25519 sig over delegation.to_json().encode()
    agent_signature_b64: str    # Agent's Ed25519 sig over same payload

@dataclass
class VerificationResult:
    valid: bool
    reason: str                 # one of the ERR_* codes, or "Valid" / "Valid chain"
    delegation_id: Optional[str]
    provider_npi: Optional[str]
    agent_id: Optional[str]
    scope: Optional[List[str]]
```

### AgentIdentityManager API

```python
m = AgentIdentityManager()
# State: m.revocation_list (agent_id → timestamp), m.revoked_delegations (delegation_id → timestamp)
# In production these dicts should be backed by Redis or a DB.

# Key generation
priv, pub = m.generate_agent_keys()           # Ed25519 keypair via cryptography library
b64 = m.public_key_to_b64(pub)               # Raw bytes → base64
pub = m.b64_to_public_key(b64)               # base64 → Ed25519PublicKey

# Create a delegation (provider grants scope to agent)
delegation = m.create_delegation(
    provider_priv,                 # Ed25519PrivateKey
    agent_id="agent-001",
    agent_pub,                     # Ed25519PublicKey
    scope=["eligibility", "claim_status"],
    ttl_seconds=86400,             # default 24h; use 0 to test expiry
    call_sid="CA123abc...",        # optional: binds passport to this specific call
    provider_npi="1234567890",     # optional: validated 10-digit NPI
)
# delegation.delegation_id is a UUID4
# delegation.nonce is SHA-256(call_sid:created_at) if call_sid provided

# Sign and package
sig = m.sign_delegation(provider_priv, delegation)
passport = m.create_agent_passport(delegation, sig, agent_priv)

# Verify a passport (payer-side verification)
result = m.verify_passport(
    passport,
    provider_pub,
    call_sid="CA123abc...",             # optional: validated against delegation.call_sid
    required_scope=["eligibility"],     # optional: ERR_SCOPE_VIOLATION if not present
)
# result.valid, result.provider_npi, result.agent_id, result.scope, result.reason

# Revocation
m.revoke_agent("agent-001")                        # revoke ALL delegations for agent_id
m.revoke_delegation(delegation.delegation_id)      # revoke one specific delegation only

# Delegation chains (e.g. provider → mid-agent → leaf-agent)
result = m.validate_chain([passport_root, passport_mid, passport_leaf], root_provider_pub)
# max MAX_CHAIN_DEPTH (3) hops
# scope must narrow or stay equal at each hop — never escalate
```

### Verification Order in `verify_passport()`

1. Agent revocation check (`agent_id in revocation_list`)
2. Delegation-ID revocation check (`delegation_id in revoked_delegations`)
3. Expiry check (`expires_at <= now`)
4. Nonce/call_sid binding (if both `delegation.call_sid` and provided `call_sid` are non-empty)
5. Provider signature verification (Ed25519 verify)
6. Agent signature verification (Ed25519 verify on same payload)
7. Required scope check (`required_scope` items must all be in `delegation.scope`)

### NPI Validation

- Regex: `^\d{10}$` — exactly 10 digits
- Empty string `""` is valid (NPI not provided)
- 9 digits, 11 digits, letters → `ValueError(ERR_INVALID_NPI)`
- Validated at `create_delegation()` time only

---

## HTTP Server: `main.py`

**Framework:** FastAPI 0.110+, Python 3.11+
**Auth:** `X-API-Key` header via `APIKeyHeader`, checked against `NHID_API_KEY` env var.
If `NHID_API_KEY` is not set in the environment, all API keys are accepted (dev mode).

### Router Auth Map

| Router file | Auth required | Endpoints |
|-------------|--------------|-----------|
| `nhid_api_endpoints.py` | Yes | `/v1/policy/evaluate`, `/v1/compliance/states` |
| `nhid_attest.py` | **No** (intentionally public) | `/v1/attest`, `/v1/attest/verify/{id}`, `/v1/attest/revoke/{id}` |
| `nhid_payer.py` | Yes | `/v1/payer/screen` |
| `nhid_audit_export.py` | Yes | `/v1/audit/log`, `/v1/audit/export/{session_id}` |

`nhid_attest` is intentionally unauthenticated so vendors can self-register without an API key.

### Endpoints

**`GET /health`** — no auth
```json
{"status": "ok", "version": "1.3.0"}
```

**`GET /v1/compliance/states`** — state AI disclosure law map
Returns: `WA_SB5395`, `IN_HB1271`, `MD_HB1563`, `UT_SB319`, `AL_SB63`, `GA_SB544`
Each entry: `{required_rules: [...], effective_date, reporting: bool, description}`

**`POST /v1/policy/evaluate`** — real-time policy decision
```json
Request:  {"session_id": "s1", "agent_id": "a1", "transcript_text": "...", "disclosure_confirmed": true}
Response: {"session_id": "s1", "action": "escalate", "reason_code": "HUMAN_ESCALATION_REQUESTED", "policy_version": "..."}
```

**`POST /v1/attest`** — issue JWT delegation token
```json
Request:  {"delegating_entity": "BCBS-provider-001", "authorized_actor": "agent-x", "scope": ["eligibility"], "expires_at": "2026-12-31T00:00:00Z"}
Response: {"reference_id": "uuid", "token": "eyJ..."}
```
Persists to SQLite at `NHID_AUTH_DB` env var path (default `nhid_auth.db`).
JWT signed with `NHID_JWT_SECRET` env var (default `nhid-dev-secret` — change in production).

**`POST /v1/payer/screen`** — payer verifies inbound AI agent call
```json
Request:  {"caller_npi": "1234567890", "reference_id": "uuid", "requested_scope": "eligibility"}
Response: {"verified": true, "compliant": true, "recommended_action": "allow", "reason": "..."}
```
Reads from same SQLite DB as `/v1/attest`. Checks: exists, not expired, not revoked, scope matches.

**`POST /v1/audit/log`** — append audit event (in-memory list; swap for DB in production)
**`GET /v1/audit/export/{session_id}?format=fhir|csv`** — export session events

**`GET /v1/certify/badge/{agent_id}`** ← **PAID FEATURE — gated behind env vars**

```
NHID_API_KEY env var must be set AND must match X-API-Key header → 403 otherwise
NHID_BADGE_TIER env var must be "L1" or "L2" → 402 if missing or invalid (free tier)
```

Returns SVG badge on success:
- `L1`: green badge "NHID-Clinical L1 Compliant" (200×20px)
- `L2`: blue badge "NHID-Clinical L2 Compliant" (200×20px)
- Cache-Control: `public, max-age=3600`

These env vars are set manually per customer account on the hosted instance.
They are **never** in the git repo, never in test fixtures, never logged.

---

## Paid Features & Pricing Model

### What Is Open vs Paid

**Open (CC BY 4.0) — anyone can use, copy, fork, self-host:**
- All Python source code (policy engine, identity library, API server)
- Conformance test suite and JSON schema
- Documentation

**Paid (requires hosted account + credentials):**
- Access to the hosted API at nhid-clinical.org (managed, SLA-backed)
- Compliance badge endpoint (`/v1/certify/badge/`) — the credential signal
- Dedicated implementation review and support
- Audit log storage with retention guarantees

### Tiers

| Tier | `NHID_BADGE_TIER` | HTTP response | What the customer gets |
|------|-------------------|---------------|------------------------|
| Free | not set | 402 on badge endpoint | Self-hosted only; no verified credential |
| L1 | `"L1"` | Green SVG badge | Hosted API + L1 badge for docs/marketing |
| L2 | `"L2"` | Blue SVG badge | L1 + audit SLA + priority support |

Billing is **not yet automated**. Env vars are set manually per account until Stripe is wired.
The 402 status code is intentional — it signals "upgrade required", not "unauthorized".

### Key Management

`NHID_API_KEY`, `NHID_JWT_SECRET`, and `NHID_BADGE_TIER` are runtime-only environment variables.
They live in the deployment environment only. Rules:
- Never commit them to the repo
- Never print them in logs or API responses
- `NHID_JWT_SECRET` default (`nhid-dev-secret`) is only safe for local dev — always override in production
- Free users self-host and get 402/403 on paid endpoints
- Paid users get the env vars set on the hosted instance by Brianna manually until billing automation is done

---

## Test Suite

**Collected: 113 tests**
**Result: 95 passed, 18 skipped, 0 failed**

The 18 skipped are HTTP integration tests that require a live server at `http://127.0.0.1:8000`.
They skip automatically and cleanly in CI — this is expected, not a problem.

### `tests/failure_injection_harness.py` — 38 tests (20 pass, 18 skip)

**20 always-pass (TestPolicyEngineUnit):** Pure unit tests for `nhid_policy_engine_v1.py`.
Cover all 5 rules + bot-to-bot + composite evaluator. No server needed.

**18 skip without server (TestInputValidation, TestChaosMode, TestPolicyEnforcement, TestReplayDeterminism):**
HTTP integration tests — null bytes, chaos headers, policy enforcement via API, replay determinism.
Run these by starting `uvicorn main:app` first.

### `tests/test_identity.py` — 25 unit tests

Coverage:
- Key generation, delegation creation, basic verify
- Expiry (`ttl_seconds=0`), agent-level revocation
- Nonce binding to call_sid (wrong SID fails)
- No nonce generated without call_sid
- NPI validation: 10 digits pass, 9 digits fail, letters fail, empty string passes
- Canonical/deterministic JSON (same object serializes identically every call)
- Tampered provider signature rejected (`ERR_INVALID_SIG`)
- Scope enforcement: subset passes, exact match passes, exceeding fails, empty scope
- Per-delegation revocation: revoke one, sibling delegations still valid
- Chain validation: single hop, two hops, scope escalation rejected, chain too long, expired link
- Performance: 1000 verifications

**Performance test platform behavior:**
```python
limit_ms = 2000 if sys.platform == "win32" else 500
# Linux (GitHub Actions / CI): 500ms enforced
# Windows (local dev): 2000ms — Ed25519 via OpenSSL has higher syscall overhead on Windows
```

### `tests/test_voice_policy.py` — 70 unit tests

Coverage:
- `check_disclosure()`: empty state, explicit False, confirmed True
- `check_escalation()`: all 6 phrases verbatim, case insensitive, embedded in sentence
- `run_voice_policy()` legacy path: disclosure first, escalation, allow, priority ordering
- `run_voice_policy()` ruleset path: custom phrases, priority, disabled rules
- Global safety phrases: 3 phrases in `_GLOBAL_SAFETY_PHRASES` always escalate even with empty phrase list or disabled rule
- Non-global legacy phrases (`transfer me`, `human agent`, `talk to someone`): suppressible by ruleset
- PHI gate: `DisclosureState` enum, `phi_gate()` raises before disclosure

### CI Invariants (`scripts/validate_ci.py`)

```
UNIT_EXPECTED = 95

Hard rules — CI fails if violated:
  counts["passed"] == 95       (exactly)
  counts["failed"] == 0
  counts["error"] == 0
  counts["skipped"] in (0, 18) # 0 = server running; 18 = no server (CI)
```

---

## CI / GitHub Actions

### `.github/workflows/ci.yml` — Unit Invariant Gate

Triggers: `push` to `main`, `claude/*`, `feature/*`; `pull_request` to `main`
Job name: `"Unit invariant: 95 passed, 0 skipped"`
Step: `python scripts/validate_ci.py` — fails CI if any invariant violated.

**When adding tests:** update both `UNIT_EXPECTED` in `validate_ci.py` AND the job name
string in `ci.yml` — they must stay in sync or the CI job name will be misleading.

### `.github/workflows/nhid-gates.yml` — Production Readiness Gates

5 parallel jobs, all must pass before `release_gate`:

| Job | What It Checks |
|-----|---------------|
| `test` | Full pytest suite with `--maxfail=1` |
| `identity_determinism` | `Delegation.to_json()` is deterministic across two calls; Ed25519 sign/verify round-trip works |
| `api_contract` | `from main import app` imports without error; `GET /openapi.json` returns 200 with `paths` key |
| `security_gates` | Tampered signature rejected; expired delegation (ttl=0) rejected; revoked agent rejected |
| `performance_smoke` | Cold start `AgentIdentityManager()` < 1s; 1000 `verify_passport()` calls < 2000ms |
| `release_gate` | Depends on all 5 — prints "ALL GATES PASSED - ELIGIBLE FOR MERGE" |

The `performance_smoke` job uses 2000ms (not 500ms) because GitHub Actions runners are shared
VMs and have variable I/O performance. The 500ms unit test limit applies to local Linux dev only.

---

## Branch Strategy

| Branch | Tests | Status |
|--------|-------|--------|
| `main` | 95 passed, 18 skipped | Stable. v1.4 fully merged via PR #212. |
| `claude/code-review-fixes-98Ir1` | 95 passed, 18 skipped | Active working branch. |
| `claude/perf-fix-98Ir1` | 95 passed, 18 skipped | Open PR → main. Windows timing fix only. |
| `feature/v1.4-auth` | superseded | Merged into main. No longer active. |

**For local development:** Work on `claude/code-review-fixes-98Ir1`. Push to that branch.
The CI gates run on every push to `claude/*` branches.

---

## Strategic Context

**Who uses this:**
- AI voice agent vendors (Prior Auth automation, RCM, eligibility bots) — embed the policy engine
- Health insurance companies (payers) — screen inbound AI calls via `/v1/payer/screen`
- Healthcare providers — verify their own agents are compliant before going live

**The pitch (to Eshan, Bek, Feros, and similar targets):**
"You're building AI that calls insurance companies. State law (WA, GA, MD, IN, UT, AL) now
requires disclosure. We're the policy engine you embed — open source, deterministic, no
vendor lock-in. Hosted API + compliance badge available for production deployments."

**State laws currently mapped:**
- WA SB5395 (effective 2025-07-27): IDG-01 + DBC-01 + EIT-01
- IN HB1271 (effective 2025-07-01): IDG-01
- MD HB1563 (effective 2026-10-01): IDG-01 + ATR-01 + reporting
- UT SB319 (effective 2025-05-07): IDG-01 + DBC-01
- AL SB63 (effective 2026-01-01): IDG-01
- GA SB544 (effective 2025-07-01): IDG-01 + EIT-01

**NIST submission:** NHID-Clinical is designed to be submitted as an open proposal to NIST's
AI governance framework for healthcare. The primary artifact is `conformance/nhid_conformance_test_suite_v1.yaml`.

**Open-core model:** Code is open because the standard has more value when it's adopted widely.
Revenue comes from the hosted service, compliance badge, and support — not the IP. Competitors
can self-host; they just won't have the verified credential from nhid-clinical.org.

---

## How to Work on This Project

### Local Setup

```bash
git clone https://github.com/thankcheeses/NHID-Clinical.git
cd NHID-Clinical
git checkout claude/code-review-fixes-98Ir1
pip install -r requirements.txt
uvicorn main:app --reload
# API docs: http://localhost:8000/docs
# OpenAPI JSON: http://localhost:8000/openapi.json
```

### Run Tests

```bash
# Quick (no server needed):
pytest tests/ -q
# Expected: 95 passed, 18 skipped in ~0.5s (Linux) or ~5s (Windows)

# Verbose:
pytest tests/ -v

# CI validation (same check GitHub runs):
python scripts/validate_ci.py
# Expected: "CI PASS"

# With live server (unlocks 18 integration tests):
uvicorn main:app &
pytest tests/ -q
# Expected: 113 passed, 0 skipped
```

### Test the Badge Endpoint (local)

```bash
# Paid tier — returns SVG:
NHID_API_KEY=mykey NHID_BADGE_TIER=L1 uvicorn main:app
curl -H "X-API-Key: mykey" http://localhost:8000/v1/certify/badge/agent-001
# → SVG response

# Wrong key → 403:
curl -H "X-API-Key: wrong" http://localhost:8000/v1/certify/badge/agent-001

# Free tier (NHID_BADGE_TIER not set) → 402:
NHID_API_KEY=mykey uvicorn main:app
curl -H "X-API-Key: mykey" http://localhost:8000/v1/certify/badge/agent-001
```

### Adding a New Policy Rule

1. Add evaluator in `src/nhid_policy_engine_v1.py` following the IDG-01 pattern
   (pure function, returns `PolicyDecision`, never raises)
2. Add it to the `decisions` list in `evaluate_all()`
3. Add the rule key to `_RULE_EVALUATORS` in `src/voice_policy.py` if voice support needed
4. Write tests — CI requires exactly `UNIT_EXPECTED` passing
5. Update `UNIT_EXPECTED` in `scripts/validate_ci.py` and the job name in `.github/workflows/ci.yml`

### Adding a New HTTP Endpoint

1. Add to the appropriate router file
2. Add Pydantic model for request/response
3. Add `dependencies=[Security(_require_api_key)]` in `main.py` router include if the endpoint is paid/protected
4. Add tests to the harness or a new test file

### Wiring the v1.4 Identity Layer to HTTP (future)

The `src/agent_identity.py` library is complete but has no HTTP API yet. To add one:
1. Create `nhid_identity.py` router with `POST /v1/identity/delegate` and `POST /v1/identity/verify`
2. Use a module-level `AgentIdentityManager` instance (or Redis-backed for production)
3. Add tests — update `UNIT_EXPECTED` and CI job name accordingly
4. This is the v1.5 milestone

---

## Files NOT to Modify Without Understanding

| File | Why it's sensitive |
|------|--------------------|
| `scripts/validate_ci.py` | `UNIT_EXPECTED = 95` — change only when test count actually changes |
| `.github/workflows/ci.yml` | Job name contains expected count; must match `validate_ci.py` |
| `src/agent_identity.py` | `to_json()` uses `sort_keys=True, separators=(',',':')` for signing — any change breaks existing signatures |
| `nhid_attest.py` + `nhid_payer.py` | Both read the same SQLite DB at `NHID_AUTH_DB` — schema changes affect both |
| `main.py` | Router wiring order matters; `nhid_attest` is intentionally public (no auth dependency) |
| `tests/test_identity.py` | Performance test uses platform-aware limit — do not remove the `sys.platform` check |
