# NHID-Clinical — Full Project Specification

**Author:** Brianna Baynard (bnbaynard@gmail.com)
**License:** CC BY 4.0
**Status:** v1.3 pilot-ready · v2 reference/preview (locked commercial tier)
**Repo:** NHID-Clinical/NHID-Clinical
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
│   └── agent_identity.py          # v2 Ed25519 cryptographic identity layer
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
│   └── validate_ci.py             # CI invariant enforcer (173 passed, 18 skipped)
├── examples/
│   └── issue_and_verify.py        # v2 end-to-end demo
├── .github/workflows/
│   ├── ci.yml                     # Unit invariant gate
│   └── nhid-gates.yml             # Production readiness gates (5 jobs)
├── requirements.txt
├── pytest.ini
└── CHANGELOG_v2.md                # v2 locked commercial tier
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
pyjwt>=2.8.0
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

## Module: `src/agent_identity.py` — Cryptographic Identity Layer (v2)

Solves NPI impersonation: any AI can look up a real provider NPI from NPPES in seconds.
A valid passport requires a cryptographic signature from the provider's private key.

**This module is a library only — it is NOT wired to any HTTP endpoint yet.**
It ships as preview/reference code. The pilot (v1.3) uses `nhid_attest.py` (JWT) instead. v2 introduces the cryptographic layer.

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
- `NHID_BADGE_TIER`: must be `"L1"` or `"L2"` → 402 if not set (free tier blocked)
