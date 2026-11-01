# Call verification and non-verbal disclosure

**Status: CANDIDATE / draft proposal.** Nothing here changes the v1.3 frozen policy
engine, the canonical control set, the enforcement ladder, any pinned baseline or any
published count. Every item marked CANDIDATE is a proposal for review, not a shipped
behaviour. Mapped, not certified.

**Source:** the research report *AI caller verification without disclosure* (revised),
read with an outside "nhid-agent blueprint" that was treated as input, not as code to
merge (see [§12](#12-disposition-of-the-outside-blueprint)).

**Fixtures:** [`fixtures/verification-nonverbal/`](../../fixtures/verification-nonverbal/)
(expected results only, not yet measured).

---

## 0. Scenario direction

This proposal stays inside the canonical scenario in
[`../canonical-threat-model.md`](../canonical-threat-model.md): **a caller-agent
telephones a payer and asks for a patient's protected information.** The caller-agent is
the party whose identity and authority must be established. The receiving party is the
payer's customer service agent or medical claims associate. Nothing below reverses those
roles.

## 1. Three trust layers

| Layer | Question it answers | Control | Status |
| :-- | :-- | :-- | :-- |
| Provider authorization | Has a provider, in a way the payer can check, authorized this agent to act for it, for this scope, until when? | DLG-01 (opt-in) | Existing. Expiry, revocation and re-attestation additions are CANDIDATE (§9). |
| Call verification | Is *this call* the one that authorization was issued for: right agent key, right number, right purpose, inside the window, not replayed, not revoked? | VER-01 | **CANDIDATE** (§4). Not part of the canonical control set. |
| Human awareness | Does the payer representative know they are dealing with an automated agent, before protected data moves, and does the agent stay truthful about it? | IDG-01, PDX-01, DBC-01 | Existing. Two-channel IDG-01 evidence is CANDIDATE (§2). |

The three layers do not substitute for each other. The distinctions the project already
holds apply unchanged:

- **Identity disclosure is not identity verification.** IDG-01 records that the agent
  said what it is. It does not establish that the claim is true.
- **Identity verification is not authorization.** A valid signature and a provider binding
  do not establish authority to receive *this* information.
- **An asserted provider affiliation establishes neither.** NPIs are public.

Corollaries used throughout: a VER-01 pass never satisfies IDG-01, and an IDG-01 pass
never satisfies VER-01.

## 2. IDG-01 with two disclosure channels (CANDIDATE evidence model)

IDG-01's requirement does not change: the receiving representative must be informed that
the counterpart is automated before protected data moves. This proposal adds a second,
separately recorded way of meeting it.

| Channel | What counts | Evidence required |
| :-- | :-- | :-- |
| **Verbal** | The representative hears the agent identify itself as automated. | Existing evidence: `disclosure_timestamp`, `identity_assertion_text`, and for an interrupted disclosure `disclosure_heard_text`. The PR #412 "heard" semantics are unchanged: a disclosure cut off before the identity statement played is not heard and must be repeated. |
| **Non-verbal** | A verified machine declaration that the caller is automated is **rendered on the representative's interface** before protected data moves. | `disclosure_channel = "non_verbal"`, `notification_rendered_at` (time of render, not time of issue), `notification_evidence` (the payer-side record that the notice was shown to this representative for this call), and `payer_optin = true`. |

Rules:

1. **A successful token exchange alone never satisfies IDG-01.** VER-01 can pass while the
   representative knows nothing; that call fails IDG-01 and PDX-01 stays gated
   (fixture FIX-VER-003).
2. **Non-verbal disclosure requires payer opt-in.** Without it, the non-verbal channel is
   `not_assessable` and a verbal disclosure is required (FIX-VER-010).
3. **Issued is not rendered.** If the payer's desktop integration is down and the notice
   is not shown, there is no non-verbal evidence, whatever the token says (FIX-VER-004).
4. **DBC-01 applies unchanged on the non-verbal path.** The agent never claims or implies
   being human and answers truthfully when asked. A rendered notice does not excuse a
   human-status claim later in the call (FIX-VER-011).
5. Each channel is recorded separately. IDG-01 passes when either channel passes on its
   own evidence. The verbal channel is always assessable; the non-verbal channel is
   `not_assessable` when the payer has not opted in or the call did not attempt it.

## 3. Measures

- **Impersonation Latency is a frozen term** (it appears in the project's comment on NIST
  docket NIST-2025-0035-0026). It is not renamed or redefined, and it stays a
  **verbal-channel** measure, as defined in [`../terminology.md`](../terminology.md).
- **Notification latency (CANDIDATE)**: elapsed time from call connect to
  `notification_rendered_at`. Non-verbal channel only.
- The two are **reported side by side and never merged** into one number. A call that
  used the non-verbal channel reports notification latency; it does not report a
  synthetic Impersonation Latency, and the existing corpora's Impersonation Latency
  figures are untouched.

## 4. VER-01: call-scoped verification (CANDIDATE)

VER-01 checks a short-lived, call-scoped token presented by the caller-agent against the
payer's server-side record of it.

**The token is bound to:**

- the originating number the call is expected from;
- the provider NPI of the provider-signed delegation (and that delegation's registry status);
- the purpose (and so the delegated scope);
- the delegation id (the same value the `nhid-agent` object carries);
- a short validity window;
- the AgentPassport key, through proof of possession at redemption.

**At redemption, the payer checks:** proof of possession of the AgentPassport key; that
the nonce and token have not been seen before (replay); that neither the token nor the
delegation is revoked; and every binding above.

**Results** use the same four values as the other controls: `pass`, `exception`,
`unknown`, `not_assessable`.

**Outcomes** come from the existing ladder only. As proposed, a VER-01 `exception` maps to
`DENY_DATA`, and the composite remains the most restrictive decision across controls. No
new outcome, metric, score or tier is introduced.

VER-01 is **not** a sixth canonical control. It is recorded here and in the optional
`call_verification` field of the trace schema so it can be reviewed and prototyped. It is
not evaluated by the v1.3 engine.

## 5. VER-01 threat model

| Topic | Proposed behaviour |
| :-- | :-- |
| **Agent authentication before issuance** | A token is issued only to a caller that (a) presents a delegation **signed by the provider** whose registry status the payer checks itself, and (b) proves possession of the AgentPassport private key named in that delegation. The payer never issues on the strength of the agent's own claims about its operator, NPI or scope. |
| **What the token is bound to** | See §4. The issuance request is itself signed and carries a random nonce, `created`/`expires` and the payer as audience (§10). |
| **Atomic single redemption** | Redemption is a single atomic compare-and-set in a store shared by every payer node that can receive the call. All binding checks run **before** the token is marked consumed, so a failed binding check does not burn a legitimate token, and a passing redemption cannot be repeated. |
| **Proof of possession** | Required at redemption, not only at issuance. A token copied from the network or read off a screen is not usable without the key. |
| **Forwarding, transfer, different number** | A call that arrives from a number other than the bound originating number fails the number binding (`exception`). An internal transfer inside the payer keeps the redeemed result for that call SID; it does not redeem again. A call forwarded through a third party that changes the presented number fails unless a new token is issued for the new number. When the presented number is unavailable (withheld, legacy trunk), the binding is `unknown`, not `pass`. |
| **Replay of recorded DTMF inside the window** | A DTMF code is a **lookup handle** for a server-side token, not a credential. The first redemption of a handle **passes**; any later redemption inside the window fails with `TOKEN_ALREADY_REDEEMED` (FIX-VER-008). Proof of possession is still required, so a recorded handle on its own is not enough even for a first redemption on a different call. |
| **Simultaneous redemption** | Two concurrent redemptions of the same token: exactly one passes and the other fails (FIX-VER-009). Which one wins is not specified. That only one wins is. |
| **Representative's screen down** | Token valid, notice not rendered: VER-01 passes, IDG-01 non-verbal evidence is absent, PDX-01 stays gated. The agent falls back to verbal disclosure or the call is escalated (FIX-VER-004). |
| **High-risk writes** | Even in scope and verified, EFT, remittance and demographic changes need out-of-band confirmation (§8, FIX-VER-012). |

## 6. Transport order

1. **Authenticated API exchange first.** The agent obtains and presents the token over an
   authenticated API (the same rails CMS-0057-F APIs and UDAP use).
2. **SIP signaling second.** Where both sides support it, the token reference rides in
   call signaling.
3. **DTMF only as a fallback for legacy IVRs.** The DTMF digits are a short lookup handle
   into the payer's server-side token record. They are not an offline-verifiable credential
   and carry no claims.

## 7. Provider proofing

VER-01 is only as good as the step that decides a provider really authorized an agent.
**Payer-portal enrollment is the leading candidate**: the provider, already authenticated
to the payer's provider portal, registers which agent keys may act for it and for what
scope. This proves the relationship **for that payer only**. It does not create a
credential another payer can rely on, and a cross-payer registry remains an open
question (§13).

## 8. High-risk writes (CANDIDATE)

Changes to EFT or bank details, remittance routing, and provider or member demographics
require **out-of-band confirmation** with the provider through a channel the payer already
holds on file, even when the delegation scope includes them and VER-01 passes. Expected
outcome: `ESCALATE_HUMAN`.

## 9. DLG-01 expiry, revocation and re-attestation (CANDIDATE)

- **Expiry:** delegations carry an expiry; VER-01 tokens never outlive their delegation.
- **Revocation:** checked at redemption as well as at issuance (FIX-VER-006).
- **Re-attestation:** the provider re-confirms long-lived delegations on a schedule set by
  the payer; a lapsed attestation is treated as revoked.

These are drafts. DLG-01's current semantics in the v1.3 engine are unchanged.

## 10. Requirements for the PR 2 prototype (NHID-Auth)

PR 2 is a separate, later change, tested independently of telephony against the
[fixtures](../../fixtures/verification-nonverbal/). It must meet all of the following:

1. **The payer verifies a provider-signed delegation and its registry status, never the
   agent's own claims.**
2. **Proof of possession** of the agent key at redemption.
3. The call-intent request carries a **nonce, `created`/`expires` and the payer
   audience**, and is signed as a **real RFC 9421 HTTP Message Signatures profile**
   (covered components and signature parameters stated, not just the label).
4. **Random nonces** from a cryptographic source; nothing derived from time or counters.
5. **Atomic single redemption in a shared store**, with every binding check run **before**
   the token is marked consumed.
6. **DTMF handles stored server-side** and **checked for collisions** at issuance.
7. **`intent_hash` is a keyed HMAC**, not a plain SHA-256 of member or claim identifiers,
   so the hash cannot be reversed by enumerating identifiers.
8. **The key fingerprint is derived from the key itself.** `key_fingerprint` in
   [`src/udap_agent_extension.py`](../../src/udap_agent_extension.py) already does this
   (SHA-256 over the raw public key bytes); PR 2 reuses it.
9. Any agent metadata **extends the existing `nhid-agent` object** from PR #403
   (`src/udap_agent_extension.py`) and **keeps `agent_id` and `call_sid`**.
10. No schema `$id` pointing at ietf.org, no claim of IETF or IANA registration, and no
    `nhid_version` 2.0. The specification is v1.3.

### PR 2 status: prototype

A CANDIDATE prototype of the payer side is in
[`src/call_verification.py`](../../src/call_verification.py), tested without telephony in
[`tests/test_call_verification.py`](../../tests/test_call_verification.py). It is not wired
into the v1.3 policy engine, the API, any adapter or the site.

| # | Requirement | Where | Tests |
| :-- | :-- | :-- | :-- |
| 1 | Provider-signed delegation and registry status, never the agent's claims | `CallVerificationService.issue`: `TrustAnchorResolver`, `validate_chain`, `PortalEnrollmentRegistry`, `verify_extension` | `test_a_self_signed_delegation_is_refused`, `test_registry_status_gates_issuance`, `test_the_agents_self_description_must_agree_with_the_delegation` |
| 2 | Proof of possession at redemption | `redeem` → `_check_possession` (`PresentationProof` against the bound key, payer-issued challenge) | `test_a_captured_handle_without_the_agent_key_fails`, `test_a_proof_for_another_challenge_fails` |
| 3 | Nonce, created/expires, audience; a stated RFC 9421 profile | `sign_call_intent`, `verify_call_intent_signature` | `test_signature_base_reproduces_rfc9421_appendix_b26`, `test_another_payers_intent_is_refused`, `test_intent_window_is_enforced`, `test_an_edited_body_breaks_the_signature` |
| 4 | Random nonces | `new_intent_nonce` (`secrets`) | `test_intent_nonces_are_random_and_distinct`, `test_a_replayed_intent_is_refused` |
| 5 | Atomic single redemption, bindings before consume | `SqliteTokenStore.consume` (conditional UPDATE), `redeem` | `test_sqlite_store_lets_exactly_one_concurrent_redemption_win`, `test_a_failed_binding_does_not_consume_the_token` |
| 6 | DTMF handles server-side, collision-checked | `TokenStore.insert` (UNIQUE), retry in `issue` | `test_a_colliding_handle_is_retried`, `test_handle_space_exhaustion_fails_closed` |
| 7 | `intent_hash` is a keyed HMAC | `intent_hmac`, `matches_intent` | `test_intent_hmac_is_keyed`, `test_the_token_record_holds_no_member_or_claim_id` |
| 8 | Key-derived fingerprint | `key_fingerprint` (reused) as RFC 9421 `keyid` | `test_fingerprint_is_derived_from_the_key`, `test_keyid_must_be_the_delegated_key_fingerprint` |
| 9 | Extend `nhid-agent`, keep `agent_id` and `call_sid` | `build_extension` / `verify_extension` (reused) | `test_agent_metadata_is_the_existing_nhid_agent_object` |
| 10 | No registration claims, no version bump | — | `test_module_makes_no_registration_or_version_claims` |

The signature base is checked against RFC 9421 Appendix B.2.6 (the Ed25519 example
reproduces exactly), and a signed call intent was also verified by an independent RFC 9421
implementation during development. Every fixture's expected `call_verification` block is
reproduced by the prototype (`test_prototype_reproduces_the_fixture_ver01_expectation`).
That is a pass/fail test of expected behaviour, not a detection rate.

## 11. Prior art

| Item | Status | Relevance |
| :-- | :-- | :-- |
| IETF [draft-hardman-verifiable-voice-protocol-08](https://datatracker.ietf.org/doc/draft-hardman-verifiable-voice-protocol/) (Verifiable Voice Protocol) | Individual Internet-Draft. Not adopted by any working group; no IETF endorsement. | Delegation evidence in SIP signaling, explicitly contemplating authority granted to "a call center proxy or an AI". Compare its credential model and SIP binding against AgentPassport and DLG-01 before aligning. |
| [RFC 9795](https://rfc-editor.org/rfc/rfc9795) (PASSporT Rich Call Data) | Published RFC. | "Vendor X signing for provider Y" through third-party PASSporTs and delegate certificates. Signed call data, not a delegation protocol; built for handset display. |
| [HL7 UDAP Security IG](https://hl7.org/fhir/us/udap-security) STU 2 | Published implementation guide. | `hl7-b2b` names the requesting organization and purpose but **has no AI-agent field**. The `nhid-agent` sibling object (PR #403) is a proposal for its documented extension slot. |
| [Visa Trusted Agent Protocol](https://developer.visa.com/docs/trusted-agent-protocol/trusted-agent-protocol-specifications) | Payment-network protocol. | **Design precedent only**: RFC 9421 signatures with `created`, `expires`, `keyid`, `nonce` and a purpose tag; short window; nonce reuse rejected. **Not deployed in payer telephony.** |
| [CMS-0057-F](https://www.cms.gov/newsroom/fact-sheets/cms-interoperability-and-prior-authorization-final-rule-cms-0057-f) | Final rule. | Provider Access, Payer-to-Payer and Prior Authorization API requirements, generally from **January 1, 2027**. It does **not** mandate agent credentials and does not specify how providers authenticate. |

## 12. Disposition of the outside blueprint

**Adopted:**

- Payer-portal enrollment as the leading provider-proofing candidate (§7), with the
  per-payer limit stated.
- Its "token valid, rep screen down" case, as FIX-VER-004, converted to this repository's
  fixture format and the four-result vocabulary.

**Not adopted, and why:**

| Blueprint element | Problem | Handling here |
| :-- | :-- | :-- |
| Delegation taken from the agent | Self-asserted; nothing a payer can check | Provider-signed delegation plus registry check (§10.1) |
| No proof of possession | A copied token is usable | Required at redemption (§10.2) |
| Touch-tone path described but not implemented | Untested claim | DTMF stays a fallback lookup handle (§6) |
| Call intent without nonce, timestamps or audience; labelled "RFC 9421" | Replayable across payers; the label is not a profile | §10.3 |
| Predictable nonce | Guessable | §10.4 |
| Replay check before the number check | Marks a token consumed before all bindings pass | Bindings first, then atomic consume (§10.5) |
| `intent_hash` as plain SHA-256 of member or claim IDs | Reversible by enumeration; can leak PHI | Keyed HMAC (§10.7) |
| Fingerprint not derived from the key | Can name a different key | §10.8 |
| Schema `$id` at ietf.org; "registered" status; `nhid_version` 2.0 | Overclaims | Not used (§10.10) |
| Schema without `agent_id` and `call_sid` | Drifts from PR #403 | Extend `nhid-agent` (§10.9) |
| State `permanently_locked` | Outside the four-result vocabulary | Not used |
| Replay fixture silent on the first redemption | Ambiguous | FIX-VER-008 states that the first redemption passes |

No IETF Internet-Draft is proposed at this stage, and the blueprint code is not converted
into unit tests.

## 13. Open questions

1. FIX-VER-004 records IDG-01 as `exception` rather than `unknown`, on the reasoning that
   a missing rendered notice is observed, not missing data. Reviewers may prefer
   `unknown`.
2. Whether the candidate fields belong in `healthcare_governance` (as drafted) or in the
   session layer that already carries the DLG-01 delegation.
3. Whether a VER-01 `exception` for an expired token should be `DENY_DATA` (as drafted) or
   `ESCALATE_HUMAN`.
4. How a provider authorized at one payer is recognized at another (cross-payer registry),
   given portal enrollment proves the relationship per payer only.
5. Whether the fixture set should get a structural test guard; left out of this change so
   that published test counts do not move.
6. No US payer was found accepting token-based AI-agent identity on phone channels. The
   design is a proposal for a gap, not a description of current practice. This document
   is not legal advice.
