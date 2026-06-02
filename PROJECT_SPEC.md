# NHID-Clinical — Full Project Specification

**Author:** Brianna Baynard (bnbaynard@gmail.com)
**License:** CC BY 4.0
**Status:** v1.3 pilot-ready · v1.4 reference/preview (not yet merged to main)
**Repo:** thankcheeses/NHID-Clinical
**Site:** nhid-clinical.org

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
cite. Timing and credibility, not secrecy.

---

## Repository Layout

```
NHID-Clinical/
├── src/
│   ├── nhid_policy_engine_v1.py   # Core NHID v1.3 rules (IDG-01 … ATR-01)
│   ├── voice_policy.py            # Voice-optimized rule engine + PHI gate
│   └── agent_identity.py          # v1.4 Ed25519 cryptographic identity layer
├── tests/
│   ├── test_voice_policy.py       # 70 unit tests for voice_policy.py
│   ├── test_identity.py           # 25 unit tests for agent_identity.py
│   ├── failure_injection_harness.py # Integration tests (18, skip without server)
│   └── trace_generator.py         # Generates synthetic audit traces
├── main.py                        # FastAPI app: wires all routers
├── nhid_api_endpoints.py          # /v1/policy/evaluate, /v1/compliance/states
├── nhid_attest.py                 # /v1/attest — JWT delegation tokens
├── nhid_payer.py                  # /v1/payer/screen — inbound call screening
├── nhid_audit_export.py           # /v1/audit/log, /v1/audit/export
├── schema/
│   └── nhid_trace_schema_v1.json  # JSON schema for audit trace events
├── conformance/
│   └── nhid_conformance_test_suite_v1.yaml # YAML conformance test spec
├── scripts/
│   └── validate_ci.py             # CI invariant enforcer (95 passed, 0 skipped)
├── examples/
│   └── issue_and_verify.py        # v1.4 end-to-end demo (on feature/v1.4-auth)
├── .github/workflows/
│   ├── ci.yml                     # Unit invariant gate
│   └── nhid-gates.yml             # Production readiness gates (5 jobs)
├── requirements.txt
├── pytest.ini
└── CHANGELOG_v1.4.md              # (on feature/v1.4-auth only)
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
    rule_id: str          # e.g. "IDG-01"
    description: str
    severity: ViolationSeverity  # CRITICAL | MAJOR | MINOR

@dataclass
class PolicyDecision:
    action: PolicyAction   # DISCLOSE_IDENTITY | ESCALATE_HUMAN | CONTINUE_AI | DENY_DATA | LOG_ONLY
    reason_code: str       # e.g. "IDG01_DISCLOSURE_MISSING"
    policy_version: str    # POLICY_ENGINE_VERSION = "1.0.0"
    violations: list[BoundaryViolation]
    next_state: str        # state machine output (e.g. "AWAITING_DISCLOSURE")
    twiml_fallback: str | None  # ready-to-use TwiML if needed
    gather_speech: bool
```

### The Five Rules

**IDG-01 — Identity Disclosure Gate**
The AI MUST proactively disclose its non-human identity at the start of every
interaction before any operational data exchange.
- Input fields: `healthcare_governance.disclosure_timestamp`, `healthcare_governance.identity_assertion_text`, `session.turn_count`, `counterparty_type`
- Pass: `disclosure_timestamp` is set AND `identity_assertion_text` is non-empty → `CONTINUE_AI`
- Fail: no `disclosure_timestamp` → `DISCLOSE_IDENTITY` + TwiML "I am an automated system"
- Bot-to-bot: stricter gate when `counterparty_type == "ai_agent"`

**PDX-01 — Pre-Data Exchange Gate**
The AI MUST NOT request or accept PHI before identity disclosure is confirmed.
- PHI trigger fields: `member_id`, `npi`, `date_of_birth`, `claim_number`, `prior_auth_number`, `diagnosis_code`, `procedure_code`, `provider_tin`
- PHI speech patterns: "member id", "date of birth", "dob", "claim number", "prior auth", "diagnosis", "procedure code", "icd", etc.
- Fail: PHI attempted before disclosure → `DENY_DATA`
- Pass with disclosure: `CONTINUE_AI` with `reason_code="PDX01_GATE_CLEARED"`

**DBC-01 — Deceptive Behavior Check**
The AI MUST NOT use deceptive audio artifacts or claim human/licensed-professional status.
- Input: `healthcare_governance.deceptive_artifact_flags` list
- Fail: any flag present → `LOG_ONLY` + `DBC01_ARTIFACT_DETECTED`

**EIT-01 — Escalation Implementation Test**
The AI MUST provide a functional path to a human operator when requested.
- Escalation triggers: "speak to a human", "real person", "supervisor", "manager", "transfer me", etc. (9 phrases)
- Fail: escalation requested but `session.escalation_path_available == False` → `ESCALATE_HUMAN` + `EIT01_NO_ESCALATION_PATH`
- Pass: escalation honored → `ESCALATE_HUMAN` + TwiML "Transferring you now"

**ATR-01 — Audit Trail Requirements**
Every event MUST carry a complete, tamper-evident audit trail.
- Required fields: `event_id`, `timestamp`, `session_id`, `request_id`, `event_type`, `actor_id`, `state_before`, `state_after`, `replay_mode`, `external_calls_cached`, `execution_context`
- Required in `execution_context`: `pipeline_version`, `policy_engine_version`, `nhid_schema_version`
- Fail: any field missing → `LOG_ONLY` + list of missing fields

**Bot-to-Bot Supplement**
When `counterparty_type == "ai_agent"`, both sides must disclose before data exchange.
Additive to IDG-01 — does not replace it.

### Composite Evaluator

```python
decision = evaluate_all(session, event)
```

Runs all 5 rules + bot-to-bot. Returns the most restrictive action.
Priority: `DENY_DATA > ESCALATE_HUMAN > DISCLOSE_IDENTITY > LOG_ONLY > CONTINUE_AI`
All violations are merged into a single list.

---

## Module: `src/voice_policy.py` — Voice Policy Engine

Optimized for real-time voice transcript evaluation. Supports both a simple legacy API
and a full rule-based path.

### Key Constants

```python
POLICY_VERSION = "VOICE-POLICY-v1.0"

# Legacy default escalation phrases (used in non-ruleset path):
_ESCALATION_PHRASES = [
    "speak to a human", "real person", "agent please",
    "transfer me", "human agent", "talk to someone",
]

# IMMUTABLE — cannot be disabled by any tenant ruleset:
_GLOBAL_SAFETY_PHRASES: tuple = (
    "speak to a human",
    "agent please",
    "real person",
)
```

### PHI State Machine

```python
class DisclosureState(str, Enum):
    AWAITING = "awaiting_disclosure_ack"
    CONFIRMED = "disclosure_confirmed"

def get_disclosure_state(session_state: dict) -> DisclosureState: ...
def phi_gate(session_state: dict, phi_fields: dict | None) -> None:
    # Raises PermissionError if PHI present before disclosure confirmed
```

### Public API

```python
result = run_voice_policy(
    transcript_text="speak to a human please",
    session_state={"disclosure_confirmed": True},
    phrases=None,           # legacy override (optional)
    policy_version=None,    # legacy override (optional)
    ruleset=None,           # preferred: list of rule dicts (optional)
    phi_fields=None,        # PHI gate input (optional)
)
# result = {"action": "escalate", "reason_code": "HUMAN_ESCALATION_REQUESTED", "policy_version": "..."}
```

**Action values:** `"disclose"` | `"escalate"` | `"allow"`

When `ruleset` is provided, rules are evaluated in ascending `priority` order.
Disabled rules (`"enabled": False`) are skipped.
After all ruleset rules, global safety phrases are checked regardless of ruleset config.

**Rule dict format:**
```python
{
    "rule_key": "HUMAN_ESCALATION_REQUESTED",
    "rule_type": "phrase_match",
    "enabled": True,
    "priority": 10,
    "params": {"phrases": ["speak to a human", "agent please"]},
}
```

Supported rule keys: `REQUIRE_UPFRONT_DISCLOSURE`, `HUMAN_ESCALATION_REQUESTED`
Supported rule types (fallback): `builtin`, `phrase_match`

---

## Module: `src/agent_identity.py` — Cryptographic Identity Layer (v1.4)

Solves NPI impersonation: any AI can look up a real provider NPI from NPPES in seconds.
A valid passport requires a cryptographic signature from the provider's private key.

**This module is a library only — it is NOT wired to any HTTP endpoint yet.**
It ships as preview/reference code. The pilot (v1.3) uses `nhid_attest.py` (JWT) instead.

### Error Codes

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
    provider_npi: str           # validated: exactly 10 digits, or ""
    agent_id: str
    agent_public_key_b64: str   # Ed25519 public key, base64-encoded
    scope: List[str]            # e.g. ["eligibility", "claim_status"]
    expires_at: int             # Unix timestamp
    created_at: int
    delegation_id: str          # UUID4
    call_sid: str = ""          # Twilio call SID (optional)
    nonce: str = ""             # SHA-256(call_sid:created_at) if call_sid set

    def to_json(self) -> str:   # Deterministic: sort_keys=True, separators=(',',':')

@dataclass
class AgentPassport:
    delegation: Delegation
    signature_b64: str          # Provider's Ed25519 sig over delegation JSON
    agent_signature_b64: str    # Agent's Ed25519 sig over same delegation JSON

@dataclass
class VerificationResult:
    valid: bool
    reason: str                 # error code or "Valid"
    delegation_id: Optional[str]
    provider_npi: Optional[str]
    agent_id: Optional[str]
    scope: Optional[List[str]]
```

### AgentIdentityManager API

```python
m = AgentIdentityManager()

# Key generation
priv, pub = m.generate_agent_keys()                    # Ed25519 keypair
b64 = m.public_key_to_b64(pub)                        # serialize
pub = m.b64_to_public_key(b64)                        # deserialize

# Create a delegation
delegation = m.create_delegation(
    provider_priv,          # Ed25519PrivateKey
    agent_id="agent-001",
    agent_pub,
    scope=["eligibility", "claim_status"],
    ttl_seconds=86400,      # default 24h
    call_sid="CA123...",    # optional: binds token to specific call
    provider_npi="1234567890",  # optional: validated 10-digit NPI
)

# Sign + issue passport
sig = m.sign_delegation(provider_priv, delegation)
passport = m.create_agent_passport(delegation, sig, agent_priv)

# Verify
result = m.verify_passport(
    passport,
    provider_pub,
    call_sid="CA123...",            # optional: must match if delegation has call_sid
    required_scope=["eligibility"], # optional: fail if scope not present
)
# result.valid == True
# result.provider_npi == "1234567890"

# Revocation (in-memory; production would use Redis/DB)
m.revoke_agent("agent-001")                       # revoke all delegations for agent
m.revoke_delegation(delegation.delegation_id)     # revoke specific delegation only

# Delegation chains (max 3 hops, scope must narrow at each hop)
result = m.validate_chain([passport_1, passport_2], root_provider_pub)
```

### Verification Order

1. Agent revocation check
2. Delegation-ID revocation check
3. Expiry check
4. Nonce/call_sid binding check (if applicable)
5. Provider signature verification (Ed25519)
6. Agent signature verification (Ed25519)
7. Required scope check

---

## HTTP Server: `main.py`

**Framework:** FastAPI
**Auth:** `X-API-Key` header, checked against `NHID_API_KEY` env var.
If `NHID_API_KEY` is not set, all keys are accepted (dev mode).

### Routers

| Router | Auth Required | Purpose |
|--------|--------------|---------|
| `nhid_api_endpoints` | Yes | Policy evaluation + state law compliance map |
| `nhid_attest` | No (self-service) | Issue JWT attestation tokens |
| `nhid_payer` | Yes | Screen inbound AI calls |
| `nhid_audit_export` | Yes | Log and export audit events |

### Endpoints

**`GET /health`** — no auth
```json
{"status": "ok", "version": "1.3.0"}
```

**`GET /v1/compliance/states`** — returns state law requirements map:
WA_SB5395, IN_HB1271, MD_HB1563, UT_SB319, AL_SB63, GA_SB544
Each entry: `{required_rules, effective_date, reporting, description}`

**`POST /v1/policy/evaluate`**
```json
{
  "session_id": "...",
  "agent_id": "...",
  "transcript_text": "speak to a human please",
  "disclosure_confirmed": true
}
```
Returns: `{session_id, action, reason_code, policy_version}`

**`POST /v1/attest`** — issues a JWT-based delegation token
```json
{
  "delegating_entity": "BCBS-provider-001",
  "authorized_actor": "agent-x",
  "scope": ["eligibility"],
  "expires_at": "2025-12-31T00:00:00Z"
}
```
Persists to SQLite (`nhid_auth.db`). Returns `{reference_id, token}`.

**`POST /v1/payer/screen`** — payer verifies an inbound AI call
```json
{"caller_npi": "1234567890", "reference_id": "...", "requested_scope": "eligibility"}
```
Looks up attestation in SQLite. Returns `{verified, compliant, recommended_action, reason}`.

**`POST /v1/audit/log`** — log an audit event (in-memory for demo; replace with DB)
**`GET /v1/audit/export/{session_id}?format=fhir|csv`** — export session audit trail

**`GET /v1/certify/badge/{agent_id}`** ← **PAID FEATURE**
Returns an SVG compliance badge. Gated by two env vars:
- `NHID_API_KEY`: must match `X-API-Key` header → 403 if mismatch
- `NHID_BADGE_TIER`: must be `"L1"` or `"L2"` → 402 if not set (free tier gets nothing)
These env vars are set per-account manually until billing is automated.
They are NEVER committed to the repo.

---

## Paid Features & Pricing Model

### What Is and Isn't Open

**Open (CC BY 4.0):**
- All source code in this repo
- Policy engine rules
- Identity layer library
- Conformance test suite
- JSON schema

**Paid (hosted service + credentials):**
- Access to the hosted API at nhid-clinical.org
- Compliance badge endpoint (`/v1/certify/badge/`)
- Dedicated support and implementation review
- SLA-backed audit log storage

### Tiers (preliminary)

| Tier | Gating | What It Unlocks |
|------|--------|-----------------|
| Free | No `NHID_BADGE_TIER` set | API access, no badge |
| L1 | `NHID_BADGE_TIER=L1` | Green "L1 Compliant" SVG badge |
| L2 | `NHID_BADGE_TIER=L2` | Blue "L2 Compliant" SVG badge + audit SLA |

**Billing is not yet automated.** Env vars are set manually per customer account.
No Stripe dependency in the codebase. The badge endpoint returns 402 on free tier.

### Keys

`NHID_API_KEY` and `NHID_BADGE_TIER` are runtime environment variables.
They live in the deployment environment only — never in the git repo, never in test fixtures.
Free users self-host and get 403/402 on paid endpoints; paid users get the env var set
on the hosted instance.

---

## Test Suite

**Total: 95 passed, 18 skipped** (on `claude/code-review-fixes-98Ir1` and `feature/v1.4-auth`)
The 18 skipped are integration tests in `failure_injection_harness.py` that require a
live server — they skip automatically in CI (expected).

### `tests/test_voice_policy.py` — 70 unit tests

Coverage:
- `check_disclosure()` — session state with/without disclosure
- `check_escalation()` — phrase matching, custom phrases, empty list
- `run_voice_policy()` legacy path — disclosure, escalation, allow
- `run_voice_policy()` ruleset path — priority ordering, disabled rules
- Global safety phrases — cannot be suppressed by empty ruleset or disabled rule
- `DisclosureState` enum and `phi_gate()` — PHI blocked before disclosure
- Parameterized tests for all 6 `_ESCALATION_PHRASES` vs global phrase behavior

**Critical behavior:** The 3 phrases in `_GLOBAL_SAFETY_PHRASES` fire as `"escalate"`
even when a custom ruleset has an empty phrase list or the escalation rule is disabled.
The other 3 phrases (`transfer me`, `human agent`, `talk to someone`) are NOT global —
they return `"allow"` when suppressed by ruleset config.

### `tests/test_identity.py` — 25 unit tests

Coverage (5 original + 20 v1.4):
- Key generation, delegation creation, basic verify
- Expiry, revocation (agent-level and delegation-level)
- Nonce binding to call_sid
- NPI validation (10 digits required; letters rejected; 9-digit rejected; empty is ok)
- Canonical/deterministic JSON serialization
- Tampered provider signature rejection
- Scope enforcement (subset passes, exact match passes, exceeding fails, empty scope)
- Per-delegation revocation (revoke one, others still valid)
- Chain validation (single hop, two hops, scope escalation rejected, too long rejected, expired link rejected)
- Performance: 1000 verifications < 500ms

### `tests/failure_injection_harness.py` — 18 integration tests

Require a live server. Skip automatically in CI (no server = expected skip).
Tests API error responses, malformed inputs, auth failures.

### CI Invariants (`scripts/validate_ci.py`)

```
UNIT_EXPECTED = 95
Hard rules:
  - passed == 95 (exactly)
  - failed == 0
  - error == 0
  - skipped in (0, 18)  # 0 = server running, 18 = CI (no server)
```

---

## CI / GitHub Actions

### `.github/workflows/ci.yml` — Unit Invariant Gate

Triggers on: `push` to `main`, `claude/*`, `feature/*`; `pull_request` to `main`
Job: "Unit invariant: 95 passed, 0 skipped"
Runs `python scripts/validate_ci.py` — fails CI if test count deviates.

### `.github/workflows/nhid-gates.yml` — Production Readiness Gates

5 parallel jobs + 1 gate job:

| Job | What It Checks |
|-----|---------------|
| `test` | Full pytest suite, `--maxfail=1` |
| `identity_determinism` | Delegation JSON is deterministic; Ed25519 sign/verify round-trip |
| `api_contract` | `from main import app` imports clean; `/openapi.json` returns 200 with `paths` |
| `security_gates` | Tampered sig rejected, expired delegation rejected, revocation enforced |
| `performance_smoke` | Cold start < 1s; 1000 verifications < 2000ms |
| `release_gate` | Depends on all 5 — "ALL GATES PASSED - ELIGIBLE FOR MERGE" |

---

## Branch Strategy

| Branch | State | Purpose |
|--------|-------|---------|
| `main` | v1.3 — 75 tests | Public, stable, matches tweet + Eshan outreach |
| `feature/v1.4-auth` | v1.4 — 95 tests | Ed25519 identity, preview/reference, NOT merged to main yet |
| `claude/code-review-fixes-98Ir1` | v1.4 — 95 tests | Active working branch |

**v1.4 merge decision:** v1.4 is the paid commercial layer. It will NOT merge to main until
there is a license model, pricing page, and monetization strategy finalized. Main intentionally
stays at v1.3 to match public communications (tweet: "75 tests passing", Eshan/Bek/Feros outreach
references v1.3 policy enforcement as the pilot).

---

## Strategic Context

**Who uses this:**
- AI voice agent vendors (Prior Auth vendors, RCM companies, payer portal automation)
- Health insurance companies (payers) screening inbound AI calls
- Healthcare providers verifying that their AI agents are compliant

**The pitch to Eshan/Bek/Feros:**
"You're making AI calls to insurance companies. We're the policy engine you embed to stay
compliant with state AI disclosure laws (WA, GA, MD, IN, UT, AL) and NIST guidelines. Open
source, deterministic, no vendor lock-in. We offer hosted API + compliance badges for production."

**NIST submission:** NHID-Clinical is designed to be submitted as an open proposal to NIST's
AI governance framework for healthcare. The conformance test suite in `conformance/` is the
artifact that gets cited.

**Open-core model:**
The code is open because the standard has more value when it's adopted widely. The revenue
model is the hosted service, the badge, and support — not the IP. Anyone can run this
themselves; they just won't have the credential that says they've been verified.

---

## How to Work on This Project

### Local Setup

```bash
git clone https://github.com/thankcheeses/NHID-Clinical.git
cd NHID-Clinical
pip install -r requirements.txt
uvicorn main:app --reload
# API at http://localhost:8000
# Docs at http://localhost:8000/docs
```

### Run Tests

```bash
pytest tests/ -q
# 95 passed, 18 skipped (normal)

python scripts/validate_ci.py
# CI PASS
```

### Test the Badge Endpoint

```bash
NHID_API_KEY=mykey NHID_BADGE_TIER=L1 uvicorn main:app
curl -H "X-API-Key: mykey" http://localhost:8000/v1/certify/badge/agent-001
# Returns SVG

curl -H "X-API-Key: wrong" http://localhost:8000/v1/certify/badge/agent-001
# 403

# Without NHID_BADGE_TIER set:
NHID_API_KEY=mykey uvicorn main:app
curl -H "X-API-Key: mykey" http://localhost:8000/v1/certify/badge/agent-001
# 402
```

### Adding a New Policy Rule

1. Add evaluator function in `src/nhid_policy_engine_v1.py` following the IDG-01 pattern
2. Add it to the `decisions` list in `evaluate_all()`
3. Add the corresponding rule key to `_RULE_EVALUATORS` in `src/voice_policy.py` if it needs voice support
4. Add tests — the CI invariant requires exactly 95 passing; add tests to match

### Adding a New HTTP Endpoint

1. Add to the appropriate router file (`nhid_api_endpoints.py` for policy, `nhid_audit_export.py` for logging, etc.)
2. Add a Pydantic model for request/response validation
3. Wire auth via `dependencies=[Security(_require_api_key)]` in `main.py` if the endpoint is gated

### v1.4 Identity Integration (future)

To wire `src/agent_identity.py` to an HTTP endpoint:
1. Add a new router (e.g. `nhid_identity.py`) with `POST /v1/identity/delegate` and `POST /v1/identity/verify`
2. Store the `AgentIdentityManager` instance (or use a Redis-backed revocation list)
3. Add tests — target count will increase above 95
4. Update `UNIT_EXPECTED` in `scripts/validate_ci.py` and the CI job name in `ci.yml`

---

## Files NOT to Modify Without Understanding

- `scripts/validate_ci.py` — changing `UNIT_EXPECTED` will break CI unless test count actually changed
- `.github/workflows/ci.yml` — the job name contains the expected count ("95 passed") — keep in sync
- `src/agent_identity.py` — the `to_json()` method uses `sort_keys=True, separators=(',',':')` for deterministic signing; changing this breaks all existing signatures
- `nhid_attest.py` — uses SQLite at `NHID_AUTH_DB` path; the `nhid_payer.py` reads the same DB; they are coupled
- `main.py` — router import order and auth dependency wiring matters; `nhid_attest` is intentionally public (no auth) so vendors can self-register
