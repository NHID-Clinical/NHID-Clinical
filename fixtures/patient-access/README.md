# Patient Access Fixtures (candidate)

Hand-authored scenarios for the candidate proposal in
[`../../docs/proposals/patient-access-authorization.md`](../../docs/proposals/patient-access-authorization.md):
the patient- and record-level access check (candidate ACC-01).

**Status:** CANDIDATE / draft · **Added:** 2026-11-01 · **Measurement:** not yet measured

> **Expected results only.** Nothing evaluates ACC-01 yet: not the v1.3 engine and not
> the VER-01 prototype. No scenario here has been run, and **no detection percentage is
> published or implied**.
>
> **Own denominator.** This set is separate from, and never pooled with, the v1 or v2
> Governance Evaluation Corpus, the Voice-Stress corpus or the
> `verification-nonverbal` fixtures. It is not a pinned baseline.

## Record shape

The same shape as `fixtures/verification-nonverbal/`: v1 corpus turn fields, a
`healthcare_governance` block on the first turn using the optional candidate fields of
`schema/nhid_trace_schema_v1.json` (each block validates against it), and per scenario:

- `expected`: per-control results in the four-result vocabulary, including `ACC-01`;
- `expected_outcome`: from the existing ladder;
- `delegated_scope`: what the provider-signed delegation covers;
- `payer_record`: what the payer's own systems hold for the case. NHID never asserts
  these facts; they are the payer's lookup, written down so the expectation is checkable;
- `measurement_status: "not_yet_measured"`.

## Cases

| ID | Case | ACC-01 | Outcome |
|----|------|--------|---------|
| FIX-ACC-001 | Claim status, claim billed by the delegating NPI | pass | CONTINUE_AI |
| FIX-ACC-002 | Claim billed by a different provider | exception `RECORD_NOT_PROVIDERS` | DENY_DATA |
| FIX-ACC-003 | Token issued for member A, agent asks about member B | exception `PATIENT_BINDING_MISMATCH` | DENY_DATA |
| FIX-ACC-004 | Eligibility for a prospective patient, provider enrolled | pass | CONTINUE_AI |
| FIX-ACC-005 | Eligibility, date of birth does not match | exception `IDENTIFIER_MISMATCH` | DENY_DATA |
| FIX-ACC-006 | Prior auth, requesting NPI matches | pass | CONTINUE_AI |
| FIX-ACC-007 | Payer claim system unavailable | unknown `PAYER_RECORD_UNAVAILABLE` | ESCALATE_HUMAN |
| FIX-ACC-008 | Group NPI on the claim, individual NPI on the delegation | unknown `GROUP_RELATIONSHIP_UNRESOLVED` | ESCALATE_HUMAN |
| FIX-ACC-009 | Eligibility-only delegation, asks for claim status | exception `SCOPE_MISMATCH` (PDX-01 already denies) | DENY_DATA |
| FIX-ACC-010 | VER-01 failed (expired token) | not_assessable `PREREQUISITE_NOT_MET` | DENY_DATA (from VER-01) |
| FIX-ACC-011 | Eligibility scope, asks for diagnosis codes | exception `MINIMUM_NECESSARY` (PDX-01 field scope) | DENY_DATA |

All names, numbers and identifiers are fictional.
