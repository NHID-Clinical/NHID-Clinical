# CHANGELOG — v1.4

## src/agent_identity.py

### Fixes

**1. NPI binding** (`create_delegation`, line 101)
- Added `provider_npi: str = ""` parameter to `create_delegation()`
- Added `_validate_npi()` — raises `ValueError(ERR_INVALID_NPI)` if value is non-empty and not a 10-digit string
- Every `Delegation` now carries the provider NPI as a verified, signed field instead of the hardcoded placeholder `"TODO"`

**2. UUID delegation IDs** (`create_delegation`, line 112)
- `delegation_id` changed from `f"del_{agent_id}_{now}"` to `str(uuid.uuid4())`
- Eliminates collisions when two delegations are created in the same second; eliminates predictable/guessable IDs

**3. Canonical signing** (`Delegation.to_json`, line 67)
- `json.dumps(asdict(self))` → `json.dumps(asdict(self), sort_keys=True, separators=(',', ':'))`
- Signing and verification now produce identical byte sequences across all Python runtimes

**4. Scope enforcement** (`verify_passport`, line 148)
- Added `required_scope: Optional[List[str]] = None` parameter
- If provided, any action in `required_scope` not present in `delegation.scope` returns `VerificationResult(False, f"{ERR_SCOPE_VIOLATION}: [missing]")`

**5. Per-delegation revocation** (`revoke_delegation`, line 163)
- Added `revoke_delegation(delegation_id: str)` method and `revoked_delegations: Dict[str, int]` store
- Revokes one specific token without affecting other active delegations for the same agent
- Existing `revoke_agent()` still available for full-agent revocation

**6. Chain validation** (`validate_chain`, line 168)
- Added `validate_chain(passports: List[AgentPassport], provider_pub) -> VerificationResult`
- Validates up to `MAX_CHAIN_DEPTH = 3` hops
- Each hop verified against the previous hop's agent public key
- Monotonic scope narrowing enforced: child scope must be a subset of parent scope (`ERR_CHAIN_NARROWING` on violation)

**7. Structured error codes** (module level, lines 32–40)
```
ERR_EXPIRED          ERR_REVOKED         ERR_INVALID_SIG
ERR_NONCE_MISMATCH   ERR_SCOPE_VIOLATION ERR_INVALID_NPI
ERR_CHAIN_NARROWING  ERR_CHAIN_TOO_LONG
```

### New imports
`re`, `uuid` added. `hashlib`, `json`, `time`, `base64` were already present.

---

## tests/test_identity.py

### New tests (20 added, 5 existing unchanged, total 25)

| Test | What it covers |
|---|---|
| `test_provider_npi_bound_in_result` | NPI in delegation is returned in `VerificationResult.provider_npi` |
| `test_invalid_npi_nine_digits_rejected` | 9-digit NPI raises `ValueError` |
| `test_invalid_npi_letters_rejected` | Alphanumeric NPI raises `ValueError` |
| `test_empty_npi_is_valid` | Empty string NPI allowed (backward compat) |
| `test_ten_digit_npi_accepted` | Valid 10-digit NPI accepted |
| `test_canonical_json_is_deterministic` | `to_json()` returns identical string on repeated calls |
| `test_tampered_provider_signature_rejected` | Single-byte mutation in sig → `ERR_INVALID_SIG` |
| `test_required_scope_subset_passes` | `required_scope` ⊆ `delegation.scope` → valid |
| `test_required_scope_exact_match_passes` | Exact match → valid |
| `test_required_scope_exceeds_delegation_fails` | `required_scope` ⊄ `delegation.scope` → `ERR_SCOPE_VIOLATION` |
| `test_empty_scope_delegation_valid` | `scope=[]` delegation verifies without `required_scope` |
| `test_empty_scope_fails_any_required_scope` | `scope=[]` fails any non-empty `required_scope` |
| `test_revoke_delegation_by_id` | `revoke_delegation(id)` invalidates that passport |
| `test_revoke_one_delegation_leaves_others_valid` | Revoking one ID leaves other delegations for same agent valid |
| `test_chain_single_hop_valid` | Single-element chain validates correctly |
| `test_chain_two_hops_valid` | Two-hop chain with scope narrowing passes |
| `test_chain_scope_escalation_rejected` | Child claims scope parent never had → `ERR_CHAIN_NARROWING` |
| `test_chain_too_long_rejected` | Chain length > `MAX_CHAIN_DEPTH` → `ERR_CHAIN_TOO_LONG` |
| `test_chain_expired_link_rejected` | Expired link in chain → `ERR_EXPIRED` |
| `test_1000_verifications_under_500ms` | 1000 `verify_passport()` calls complete in < 500ms |

**Test count:** 75 (v1.3) → 95 passed, 18 skipped (v1.4)

---

## examples/issue_and_verify.py (new file)

Runnable end-to-end demo. Covers: keypair generation, NPI-bound delegation, passport creation and verification, scope enforcement (pass and fail cases), per-delegation revocation, and 2-hop chain validation. All assertions embedded; run with `python examples/issue_and_verify.py`.

---

## scripts/validate_ci.py

`UNIT_EXPECTED` updated from `75` to `95`.

## .github/workflows/ci.yml

Job name and comments updated from `75` to `95`. `feature/*` branches added to CI trigger.
