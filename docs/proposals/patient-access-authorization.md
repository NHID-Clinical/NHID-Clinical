# Patient- and record-level access (candidate ACC-01)

**Status: CANDIDATE / draft proposal.** Nothing here changes the v1.3 frozen policy
engine, the canonical control set, the enforcement ladder, any pinned baseline or any
published count. ACC-01 is **not** a sixth canonical control. Mapped, not certified.
Not legal advice.

**Follows:** [`verification-and-nonverbal-disclosure.md`](verification-and-nonverbal-disclosure.md)
(VER-01, call-scoped verification, with its prototype in
[`src/call_verification.py`](../../src/call_verification.py)).

**Fixtures:** [`fixtures/patient-access/`](../../fixtures/patient-access/) (expected
results only, not yet measured).

---

## 0. Scenario direction

Unchanged from [`../canonical-threat-model.md`](../canonical-threat-model.md): **a
caller-agent telephones a payer and asks for a patient's protected information.** The
payer's representative is the receiving party. The patient is usually not on the call.

## 1. The question this answers

A payer facing an AI caller has four questions. The first three already have answers in
this repository; the fourth does not.

| Question | What answers it today |
| :-- | :-- |
| Is this caller automated, and did it say so before asking for anything? | IDG-01, PDX-01, DBC-01 (v1.3 engine) |
| Is it the agent it claims to be, sent by this provider? | NHID-Auth (`AgentIdentityManager.validate_chain`, provider-signed delegation, revocation) and, as a candidate, VER-01 (`src/call_verification.py`: payer-held trust anchors, portal enrollment, proof of possession, single redemption) |
| May it ask this *kind* of question? | DLG-01 (opt-in) with PDX-01: requested fields are checked against the delegated scope (`_SCOPE_PERMITTED_FIELDS` in `src/nhid_policy_engine_v1.py`); outside it, `PDX01_SCOPE_NOT_AUTHORIZED` |
| May it see **this patient's record**, for this purpose? | **Nothing yet.** That is ACC-01 |

The gap, concretely: an agent with a valid key, a valid provider-signed delegation, an
active enrollment, a valid RFC 9421 request signature and a token that redeems once
asks for the status of a claim **another practice billed**. Every existing check
passes. The project's own rule already says this is not enough: identity verification
is not authorization, and does not establish authority to receive *this* information.

One piece already exists. The VER-01 prototype binds each token to the member and
claim the agent declared at issuance, as a keyed HMAC (`intent_hmac`), and
`matches_intent()` tells the payer whether the record the representative opens is that
one. That stops a token minted for one patient being used for another. It does not say
whether the patient or claim is this provider's.

## 2. Principle: the payer decides, from its own records

Only the payer knows that claim 12345 was billed under NPI X, that a prior
authorization case was requested by NPI Y, or that a member ID and date of birth belong
together. NHID-Clinical cannot and does not assert any of that.

So ACC-01 is not a decision engine of its own. It specifies **which verified inputs the
payer compares against which of its own records**, and what happens when they do not
line up:

* from NHID: the delegating NPI (from the signed delegation, never from the caller's
  speech), the delegated scope, the declared purpose, and the VER-01 patient binding;
* from the payer: the claim, case or member record it already holds.

## 3. Checks (candidate)

Results use the four values every control uses: `pass`, `exception`, `unknown`,
`not_assessable`.

| Check | Passes when |
| :-- | :-- |
| `patient_binding` | The record the representative opens matches the token's `intent_hmac` (`matches_intent`). |
| `identifier_match` | The member identifiers given (member ID, date of birth) match the payer's record. |
| `record_relationship` | Per operation, below. |
| `purpose` | The declared purpose is inside the delegated scope (the existing `check_purpose_of_use` cross-check in `src/udap_agent_extension.py`). |
| `minimum_necessary` | The fields requested are within what the operation needs. **Already enforced** field by field by PDX-01 scope; ACC-01 records it and adds no second mechanism. |

`record_relationship`, per operation:

| Operation | Relationship tested |
| :-- | :-- |
| `claim_status` | The claim's billing or rendering NPI equals the delegating NPI. |
| `prior_auth` | The case's requesting or servicing NPI equals the delegating NPI. |
| `eligibility` | **No prior relationship is required.** Checking coverage before a first visit is normal. What is tested is that the provider is enrolled with this payer (the same per-payer enrollment VER-01 uses). |

**Prerequisite.** If VER-01 or DLG-01 has not passed, ACC-01 is `not_assessable`.
Access is never evaluated for a caller whose identity and delegation are unverified, and
`not_assessable` is never read as a pass.

## 4. Outcomes

From the existing ladder only:

| ACC-01 result | Outcome |
| :-- | :-- |
| `pass` | No restriction from ACC-01. The composite is still the most restrictive decision across every control. |
| `exception` | `DENY_DATA` |
| `unknown` (record unavailable, or an unresolved group/individual NPI relationship) | `ESCALATE_HUMAN` |
| `not_assessable` | Whatever the failed prerequisite already decided (VER-01 or DLG-01) |

High-risk writes (EFT, remittance, demographic changes) still need out-of-band
confirmation, as in the VER-01 proposal §8, whatever ACC-01 says.

## 5. Evidence

An optional trace field, `healthcare_governance.access_authorization`, records the
result, reason code, operation and each check. It carries **no PHI in clear**: patient
references stay as the keyed HMAC VER-01 already uses, and the payer's record values are
not copied into the trace. Whether the full evidence belongs in this trace or only in
the payer's own audit system is an open question (§9).

## 6. Legal framing (to be confirmed by counsel)

Stated carefully, because the difference matters:

* Disclosures to a provider for the provider's payment activities (eligibility, claim
  status, prior authorization) generally fall under HIPAA's permitted uses and
  disclosures for treatment, payment and health care operations, and do **not**
  generally require a patient's signed authorization. ACC-01 therefore does not ask for
  patient consent per call.
* What still applies to the payer: verifying the identity and authority of whoever is
  requesting, and limiting the release to the minimum necessary. ACC-01 is a structured
  way to show that both were checked for an AI caller.
* Exact provisions, and anything stricter under state law or the payer's own policy,
  are for counsel. Nothing in this proposal is a compliance claim.

## 7. Context and prior art

* **X12 276/277 claim status** already keys a claim status inquiry to provider
  identifiers: on the electronic rail, a payer answers about claims tied to the
  requesting provider. ACC-01 asks for the same discipline on the voice channel.
* **CMS-0057-F Provider Access API** limits data sharing to providers with a treatment
  relationship established through attribution. That is an API rail, not telephony, but
  it is the same idea: data follows a relationship the payer can check, not a claim the
  caller makes.

## 8. Requirements for a later prototype

Not started. When it is, it extends `src/call_verification.py`; it is not a parallel
engine.

1. The payer record lookup is an interface (claim, case, member), so the prototype is
   tested against fixtures without any payer system.
2. Every check runs before anything is released; a failed check never partially releases.
3. NPI comparison is exact. Group and individual NPI handling follows whatever §9 decides,
   and until then is `unknown`.
4. The delegating NPI comes only from the verified delegation, never from speech or from
   the agent's own metadata.
5. Results serialize to `access_authorization` and validate against the trace schema.
6. Every fixture in `fixtures/patient-access/` is reproduced.

## 9. Open questions

1. **Group and TIN relationships.** A claim billed under a group (type 2) NPI when the
   delegation is from an individual (type 1) NPI in that group. Drafted as `unknown`,
   so a human decides (FIX-ACC-008). A payer may hold the group membership and resolve it.
2. **Eligibility without a prior relationship.** Drafted as allowed for an enrolled
   provider. Some payers may want more (for example, an appointment reference).
3. **Where the evidence lives.** The trace field, the payer's own audit, or both.
4. **Rendering vs billing NPI** for claim status: drafted as either.

---

*NHID-Clinical is an independent research project and reference implementation. Nothing
here claims production deployment, healthcare-provider adoption, HIPAA certification or
independent validation. See [`../claim-boundaries.md`](../claim-boundaries.md).*
