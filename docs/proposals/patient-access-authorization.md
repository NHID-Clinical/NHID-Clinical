# Record-level access for delegated AI agents (candidate ACC-01)

**Status: CANDIDATE / draft proposal.** Nothing here changes the v1.3 frozen policy
engine, the canonical control set, the enforcement ladder, any pinned baseline or any
published count. ACC-01 is **not** a sixth canonical control and is **not** an
implemented NHID-Clinical capability. Mapped, not certified. Not legal advice.

**Follows:** [`verification-and-nonverbal-disclosure.md`](verification-and-nonverbal-disclosure.md)
(VER-01, call-scoped verification; prototype in
[`src/call_verification.py`](../../src/call_verification.py)).

**Fixtures:** [`fixtures/patient-access/`](../../fixtures/patient-access/) (expected
results only, not yet measured).

---

## 0. What this proposal is, and is not

This is **not** a new patient-access authorization system. Payers already decide which
providers may see which members' data, and established implementations already match a
requesting provider to a claim (§7). ACC-01 specifies **how a verified AI agent's
delegation should feed into the payer's own record-level disclosure decision**, on the
telephone channel, before anything is released.

The scenario is unchanged from [`../canonical-threat-model.md`](../canonical-threat-model.md):
**a caller-agent telephones a payer and asks for a patient's protected information.**
The payer's representative is the receiving party. The patient is usually not on the call.

## 1. Where NHID-Clinical stands

| Capability | Status |
| :-- | :-- |
| AI agent disclosure | **Built**: IDG-01 |
| No protected data before disclosure | **Built**: PDX-01 |
| No human-status claims | **Built**: DBC-01 |
| Provider-signed delegation | **Built**: NHID-Auth (`AgentIdentityManager.validate_chain`), evaluated by DLG-01 |
| Delegated field scope | **Built, opt-in**: with DLG-01 on, PDX-01 checks requested fields against `_SCOPE_PERMITTED_FIELDS` (`src/nhid_policy_engine_v1.py`) and denies with `PDX01_SCOPE_NOT_AUTHORIZED` |
| Call-scoped verification and patient/claim token binding | **Prototype**: VER-01 in `src/call_verification.py` (#439), not wired into the engine. `intent_hmac` / `matches_intent` bind a token to a member and claim reference |
| Provider-to-record relationship, and the payer-side access decision | **Candidate**: ACC-01, this proposal |

The four questions a payer faces, and where each is answered:

1. Who is the AI agent? (NHID-Auth, VER-01 prototype)
2. Which provider authorized it? (NHID-Auth, DLG-01)
3. What information may it request? (PDX-01 field scope under DLG-01)
4. **Is the requested record authorized for disclosure to that delegated agent?** (ACC-01, candidate)

The gap in one sentence: an agent with a valid key, a valid provider-signed delegation,
an active enrollment, a valid request signature and a token that redeems once can still
ask about a claim no evidence ties to its provider, and every built check passes.

## 2. Principle: the payer decides, from its own records, under its own policy

NHID supplies **verified inputs**:

* the delegating NPI, from the signed delegation, never from the caller's speech or the
  agent's own metadata;
* the delegated scope and declared purpose;
* the VER-01 resource binding (§3.1).

The payer supplies the **evidence and the policy**: its claim, case and member records,
its provider directory, and which relationship types it accepts (§3.3). NHID never
asserts a provider-patient relationship.

## 3. Checks (candidate)

Results use the four values every control uses: `pass`, `exception`, `unknown`,
`not_assessable`.

### 3.1 `patient_binding`, per operation

The VER-01 prototype's `intent_hmac` covers a member reference and a claim reference.
A claim binding is **not** a universal patient or record binding. Each operation binds
its own resource (`resource_binding.type` in the trace):

| Operation | Required binding | `resource_binding.type` | Prototype today |
| :-- | :-- | :-- | :-- |
| `eligibility` | member ID + date of birth + eligibility request reference | `MEMBER_ELIGIBILITY_REQUEST` | **partial**: member only; no DOB or request reference |
| `claim_status` | member ID + claim reference | `MEMBER_CLAIM` | covered |
| `prior_auth` | member ID + authorization/case reference | `MEMBER_AUTH_CASE` | **not covered** |

`patient_binding` passes when the resource the representative opens is the bound one. The
binding reference is a keyed HMAC of these identifiers, never the identifiers.

### 3.2 `identifier_match`

The member identifiers given (member ID, date of birth) match the payer's record. This is
the check a payer already applies to a human caller.

### 3.3 `record_relationship`: payer-defined evidence, not one NPI rule

Two different decisions must not be confused:

* **member-level attribution**: "this provider is associated with this member", which
  is what Provider Access API attribution establishes (§7);
* **record-level link**: "*this* claim or authorization is linked to the delegating
  provider".

The payer states which evidence it recognizes for each operation, and the trace records
which one established the relationship (`relationship_basis`):

| `relationship_basis` | Meaning |
| :-- | :-- |
| `CLAIM_BILLING_PROVIDER` | The delegating provider is the billing provider on the claim. |
| `CLAIM_RENDERING_PROVIDER` | The delegating provider is the rendering provider on the claim. |
| `PRIOR_AUTH_REQUESTING_PROVIDER` | The delegating provider requested the authorization. |
| `PRIOR_AUTH_SERVICING_PROVIDER` | The delegating provider is the servicing provider on the authorization. |
| `PAYER_ATTRIBUTION` | The payer attributes the member to the delegating provider (for example from historical claims). |
| `ORGANIZATIONAL_MEMBERSHIP` | The payer's directory places the delegating provider in the organization on the record. |
| `UPCOMING_APPOINTMENT` | The payer has **verified** an upcoming appointment with the delegating provider. |
| `UNKNOWN` | The evidence could not be determined. Never a pass; escalates. |

Exact NPI equality is not hardcoded. The decisions this proposal takes:

| Operation | Question | Rule |
| :-- | :-- | :-- |
| `eligibility` | Is there an acceptable basis for this provider to check this patient's coverage? | Existing patient: `PAYER_ATTRIBUTION`. **New patient: `UPCOMING_APPOINTMENT`, verified by the payer.** An appointment the agent asserts is not evidence. No basis: `unknown`, escalate. |
| `claim_status` | Is this specific claim linked to this provider? | **Linked claims only**: `CLAIM_BILLING_PROVIDER`, `CLAIM_RENDERING_PROVIDER` or `ORGANIZATIONAL_MEMBERSHIP`, as the payer's policy recognizes. Member attribution alone does **not** open the member's other claims. Evidence that the claim is someone else's: `exception`, deny. No evidence either way: `unknown`, escalate. |
| `prior_auth` | Is this specific authorization linked to this provider? | `PRIOR_AUTH_REQUESTING_PROVIDER`, `PRIOR_AUTH_SERVICING_PROVIDER` or `ORGANIZATIONAL_MEMBERSHIP`. |

The appointment rule is a **proposed payer policy**, following the CMS Provider Access
FAQ's example that payers "could accept proof of an upcoming appointment" for new
patients. It is not a CMS mandate.

### 3.4 `purpose`

The declared purpose is inside the delegated scope: the existing `check_purpose_of_use`
cross-check in `src/udap_agent_extension.py`.

### 3.5 Minimum necessary is not an ACC-01 check

PDX-01 already enforces field scope under DLG-01. ACC-01 does not duplicate it.
ACC-01 is evaluated only after field scope passes.

### 3.6 Prerequisites

ACC-01 is `not_assessable` unless VER-01, DLG-01 and PDX-01 field scope have passed.
Access is never evaluated for an unverified caller or an out-of-scope request, and
`not_assessable` is never read as a pass.

## 4. Outcomes

From the existing ladder only:

| ACC-01 result | Outcome |
| :-- | :-- |
| `pass` | No restriction from ACC-01. The composite is still the most restrictive decision across every control. |
| `exception` | `DENY_DATA` |
| `unknown` (record unavailable, relationship evidence unresolved) | `ESCALATE_HUMAN` |
| `not_assessable` | Whatever the failed prerequisite already decided |

High-risk writes (EFT, remittance, demographic changes) still need out-of-band
confirmation, as in the VER-01 proposal §8, whatever ACC-01 says.

## 5. Evidence

An optional trace field, `healthcare_governance.access_authorization`, records the
result, reason code, operation, `relationship_basis` and each check. It carries **no PHI
in clear**: resource references stay as the keyed HMAC VER-01 already uses, and the
payer's record values are not copied into the trace.

## 6. Legal framing (to be confirmed by counsel)

* Disclosures to a provider for the provider's payment activities generally fall under
  HIPAA's permitted uses and disclosures for treatment, payment and health care
  operations, and do **not** generally require a patient's signed authorization. ACC-01
  therefore does not ask for patient consent per call.
* What still applies: verifying the identity and authority of whoever is requesting, and
  the minimum-necessary rule (handled by PDX-01).
* Exact provisions, state law and payer policy are for counsel. Nothing in this proposal
  is a compliance claim.

## 7. Prior art

Other implementations document substantial parts of this. These were checked against
their public documentation on 1 November 2026:

| Implementation | What it documents | Relation to ACC-01 |
| :-- | :-- | :-- |
| **CMS Provider Access API FAQ** (CMS-0057-F) | Payers determine whether a provider has a treatment relationship "using a patient attribution process"; CMS "did not require impacted payers to use a particular attribution process or standard". For new patients, "payers could accept proof of an upcoming appointment"; for ongoing relationships, "historical claims data can be used". | The policy context. Member-level attribution, over an API, not telephony. Informs the eligibility open question (§9). |
| **CareEvolution Orchestrate**, Provider Access API | Access requires a paid claim that "References a practitioner or organization associated with the provider requesting the data", comparing "the provider and payee.party fields of the claim with the NPI information specified during provider setup", and the provider directory "to see if the practitioner/organization belongs to the requesting provider". | The closest documented match: payer-held claims and a directory establishing the provider relationship, including group membership. It establishes member-level access, not release of the one matched claim. |
| **Stedi**, claim status checks | "The billing provider NPI must match the one submitted in the claim." Use the organizational NPI if the practice bills under a group NPI; "Some payers index claims by the rendering provider rather than the billing organization." | Provider-to-claim matching on the 276/277 rail is established practice. It is documented as transaction matching, not as an authorization gate tied to a verified delegation. |
| **OpenFGA**, healthcare model | Care-team relationships grant `can_view_record`; a separate `can_view_sensitive` gates PHI fields; records inherit visibility from the encounter and patient. | Relationship-based authorization as an architectural pattern; not a payer record lookup. |
| **X12 276/277** | Claim status inquiry keyed to provider identifiers. | The electronic rail ACC-01 mirrors on the voice channel. |

Named in the research input but **not verified in this review**, to examine before any
public comparison: Salesforce Agentforce for Payer and Provider Contact Centers, the CMS
HETS third-party vendor enrollment requirement, Firely Server's Provider Access
guidance, Availity provider workflows, Da Vinci PDex attribution groups, and SMART on
FHIR patient-context scopes.

**What is proposed here.** ACC-01 proposes a payer-side, record-level authorization
contract for AI agents in provider-to-payer telephony. It combines cryptographically
verified agent delegation, operation-specific patient and record binding, payer-held
provider relationship evidence under a stated policy, and delegated purpose limits, with
minimum necessary left to the existing PDX-01 field scope. The implementations reviewed
document payer-held attribution, provider-to-claim NPI matching and relationship-based
authorization. They do not document this complete combination. This review does not
establish that no equivalent implementation exists.

## 8. Requirements for a later prototype

Not started. When it is, it extends `src/call_verification.py`; it is not a parallel
engine.

1. **Typed resource binding.** Replace the member/claim pair in `intent_hmac` with a typed
   resource binding (`MEMBER_ELIGIBILITY_REQUEST`, `MEMBER_CLAIM`, `MEMBER_AUTH_CASE`), so
   eligibility binds the date of birth and request reference and prior authorization binds
   its case.
2. **Payer record lookup as an interface** (claim, case, member, directory), so the
   prototype is tested against fixtures without any payer system.
3. **Relationship policy as data.** The accepted evidence types per operation are
   configuration, and the result records which one matched.
4. Every check runs before anything is released; there is no partial release.
5. The delegating NPI comes only from the verified delegation.
6. Results serialize to `access_authorization` and validate against the trace schema.
7. Every fixture in `fixtures/patient-access/` is reproduced. The fixtures are generated by
   `scripts/build_patient_access_fixtures.py`, which refuses to write a scenario that breaks
   the binding, relationship-basis or upstream-minimum-necessary invariants
   (`--check` verifies the committed copy).

## 9. Decisions and open questions

Decided for this proposal:

1. **New-patient eligibility requires appointment proof the payer verifies.** Enrollment
   alone is not enough; without it the result is `unknown` and escalates.
2. **Claim status releases linked claims only.** A provider attributed to a member still
   cannot read that member's unrelated claims.

Still open:

1. **Accepted evidence per operation.** The fixtures assume one example policy
   (`payer_policy_assumed` in their metadata); each payer chooses its own.
2. **How a payer verifies an appointment** (scheduling feed, prior-authorization record,
   referral), and how far ahead it may be.
3. **Where the evidence lives.** The trace field, the payer's own audit, or both.

---

*NHID-Clinical is an independent research project and reference implementation. Nothing
here claims production deployment, healthcare-provider adoption, HIPAA certification or
independent validation. See [`../claim-boundaries.md`](../claim-boundaries.md).*
