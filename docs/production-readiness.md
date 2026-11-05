# What stands between NHID-Clinical / NHID-Auth and production use

The project is at the **Research** stage ([`claim-boundaries.md`](claim-boundaries.md)).
This document records the open decisions a production or enterprise deployment
would need, one per issue under the map in #457. It is a decision record, not a
claim. Nothing in it may be read or quoted as "production ready" or "enterprise
ready", and no item is closed until the evidence named for it is on file.

Each section gives:
- the question;
- what exists today;
- the options;
- the recommended direction;
- the evidence that would close it;
- what may be said at the current stage.

Mechanics already written down live in
[`nhid-auth-pki-and-oauth2-integration.md`](nhid-auth-pki-and-oauth2-integration.md)
(the PKI and OAuth guide), and this document points to it rather than repeat
it. It adds no control, outcome or metric.

| # | Decision | Recommended direction | Status |
| :-- | :-- | :-- | :-- |
| 1 | Key custody (#458) | Signer interface; AWS KMS `ECC_NIST_EDWARDS25519` first | Open |
| 2 | Trust anchors and revocation across organizations (#459) | Provider-hosted key set plus a W3C Bitstring Status List | Open |
| 3 | OAuth token exchange / identity chaining (#460) | A profile document mapping NHID-Auth to RFC 8693 | Open |
| 4 | STIR/SHAKEN and Rich Call Data (#461) | Keep the passport out of band; an RCD pointer is optional later | Open |
| 5 | HIPAA verification mapping (#462) | A mapping for counsel review; no compliance claim | Open |
| 6 | Shared challenge store (#463) | DynamoDB with a TTL, the same shape as the call-verification store | Open |
| 7 | NIST NCCoE (#464) | Offer the scenario, Ida and the corpus as input | Open |

---

## 1. Key custody: HSM or KMS (#458)

**Question.** Where do signing keys live, who can use them, and how do they
rotate?

**Today:**
- **Provider delegation keys (NHID-Auth issuers)** exist only as in-process
  objects. There is no persistence, no KMS and no HSM
  (`claim-boundaries.md`, "Key custody / per-tenant isolation").
- **Audit event and anchor keys** rotate with a retired-key list but live in
  environment variables (`AUDIT_SECRET_KEYS_RETIRED_B64`,
  `AUDIT_ANCHOR_KEYS_RETIRED_B64`; `src/preflight.py`).
- **Ida's demonstration keys** are environment values from
  `scripts/ida_demo_credentials.py` and are never production keys.

**Options:**
- a cloud KMS with asymmetric Ed25519 signing;
- a cloud HSM through PKCS#11;
- each organization's own key service behind a signer interface.

**Recommended direction.**
- Put a `Signer` interface in front of every signing call in
  `src/agent_identity.py`: `sign(bytes) -> signature`, `public_key`, `kid`.
  Keep the in-process key as one implementation, for tests and the
  demonstration.
- Write a second implementation on AWS KMS. KMS offers Ed25519 as key spec
  `ECC_NIST_EDWARDS25519`, sign/verify only, with `ED25519_SHA_512` over a RAW
  message. The private key never leaves KMS.
- Rotation stays by `kid`: a new key gets a new `kid`, and verifiers keep
  retired public keys. The `kid` field already exists in `Delegation`.
- The audit HMAC keys can move to KMS HMAC keys behind the same kind of
  interface.
- Operations: PKI and OAuth guide §1.11.

**Evidence that closes it:**
- a KMS-backed signer exercised in CI against a real or emulated KMS;
- a rotation drill: sign with key A, rotate to B, verify both, revoke A;
- an IAM policy granting `kms:Sign` only to the issuing role.

**May be said now:** "Key custody is a documented design, not built."

## 2. Trust anchors and revocation across organizations (#459)

**Question.** How does a payer learn a provider's current keys, and how does a
revocation reach a payer in another organization?

**Today:**
- A payer configures `NHID_TRUST_ANCHORS` by hand, as `NPI:public-key:kid`
  entries.
- Revocation is durable inside one deployment (`revoked_delegations`,
  `nhid_event_store.is_delegation_revoked`) and does not propagate across
  organizations (`claim-boundaries.md`, "Revocation").

**Options:**
- static exchange, as today;
- a key set the provider hosts at a known HTTPS location, in JWKS style;
- a published revocation list;
- a registry from NPI to key, run by a third party.

**Recommended direction.**
- **Keys:** a provider-hosted key set, fetched and cached by the payer, with
  the `kid` selecting the key (PKI and OAuth guide §1.8).
- **Revocation:** each delegation carries a status-list index, and the issuer
  publishes a W3C **Bitstring Status List v1.0** (a W3C Recommendation, 15 May
  2025). The default list is 131,072 entries, about 16 KB before compression,
  and the payer caches it with a short time to live. The payer's
  `revocation_checker` reads the cached list.
- **Registry:** a registry from NPI to key stays Future. It needs an operator,
  and that is a counterparty decision, not code.

**Evidence that closes it:**
- two separately deployed parties, each with its own keys;
- a revocation by one party is enforced by the other within the cache
  lifetime;
- the failure behaviour is tested: when the list is unreachable, the answer
  is fail-closed or a cached answer, and the choice is recorded.

**May be said now:** "Revocation is durable within one deployment; it does not
propagate across organizations."

## 3. OAuth token exchange and identity chaining (#460)

**Question.** Can a payer verify an NHID-Auth delegation with standard OAuth
tooling instead of NHID-specific code?

**Today:**
- NHID-Auth has its own `Delegation`, `AgentPassport` and `PresentationProof`
  (`src/agent_identity.py`).
- The PKI and OAuth guide, Part 2, explains how NHID-Auth coexists with
  OAuth 2.0 and OIDC. It does not replace them.

**Relevant standards:**
- **RFC 8693, OAuth 2.0 Token Exchange.** It exchanges one token for another,
  with actor and subject semantics.
- **`draft-ietf-oauth-identity-chaining`** (IETF OAuth working group,
  Standards Track; revision -11, May 2026). It combines RFC 8693 with the JWT
  authorization grant to carry identity across trust domains. It is a draft,
  so check its current status on the IETF datatracker before relying on it.

**Recommended direction.** Write a profile document before any code. The
mapping:

| NHID-Auth | OAuth |
| :-- | :-- |
| Practice (issuer) | Authorization server in the provider's domain |
| Ida (agent) | Actor (`act` claim) |
| Patient's workflow scope | `scope` |
| Call binding | Audience and a call-bound claim |
| Proof of possession | DPoP or an equivalent sender-constrained token |

The profile also records what stays NHID-specific, for example the NPI
binding.

**Evidence that closes it:**
- the profile, reviewed by someone outside the project;
- one end-to-end exchange using an off-the-shelf authorization server.

**May be said now:** "Designed to coexist with OAuth 2.0; a token-exchange
profile is open work."

## 4. STIR/SHAKEN and Rich Call Data (#461)

**Question.** Should the passport ride on the phone network?

**Today:**
- STIR/SHAKEN attests that the calling number is legitimate.
- **RFC 9795**, the PASSporT extension for Rich Call Data (July 2025), lets a
  signed token carry caller name, logo and call reason.
- Neither standard says that this agent may receive this patient's
  information.
- Ida presents her passport out of band, over HTTPS, bound to the call
  ([`reference-agent.md`](reference-agent.md)). No SIP path carries one.

**Options:**
- keep it out of band;
- put a pointer to the passport (not the passport) in an RCD claim;
- carry the passport in SIP.

**Recommended direction.**
- Keep the passport out of band. It carries scope and a proof of possession
  that carrier attestation was not built for, and the payer verifies it in its
  own systems either way.
- An RCD pointer, a URL or a delegation id, is optional later work. It is
  worth doing only once one carrier and one payer want it.

**Evidence that closes it:** a written position checked with someone who
operates STIR/SHAKEN signing, and, if a pointer is wanted, a test call carrying
one.

**May be said now:** "Carrier attestation proves the number and the brand,
not authority. No SIP path carries a passport."

## 5. HIPAA verification mapping, 45 CFR 164.514(h) (#462)

**Question.** How do the controls line up with the Privacy Rule's requirement
that a covered entity verify the identity and the authority of a person
requesting PHI who is not known to it?

**Status.** **This mapping is for counsel review. It is not legal advice and
supports no compliance claim.** The counsel review of the HIPAA framing is
also what moves the project from Research to Pilot-ready
(`claim-boundaries.md`).

**Draft mapping:**

| What 164.514(h) asks the covered entity to establish | Evidence the reference implementation can produce | What it does not establish |
| :-- | :-- | :-- |
| That the requester is who they say they are | IDG-01: the agent disclosed it is not human. DLG-01 (opt-in): a passport signed by a trusted provider key, bound to the call, with proof of possession. | That the provider key belongs to the organization named, unless the payer configured that anchor itself. Identity disclosure is not identity verification. |
| That the requester has authority to receive this information | DLG-01 scope, and PDX-01 denying fields outside the delegation | That the delegation was right to grant, or that the patient relationship exists |
| That verification happened before disclosure | PDX-01 sequencing: no protected data before disclosure, and a denial when the checks fail | Anything about calls the engine never saw |
| A record of what was relied on | ATR-01 audit trail, with the delegation id and the decision | Tamper-proof storage. ATR-01 detects modification; it does not prevent it (`claim-boundaries.md`). |

The rule also lets a covered entity rely on documentation, statements or
representations that on their face meet its requirements. Whether a verified
delegation counts as such documentation is the core question for counsel.

**Evidence that closes it:** a counsel's written review of this mapping and of
the HIPAA framing across the site.

**May be said now:** "A mapping prepared for counsel review." Never
"HIPAA-compliant" or "HIPAA-certified".

## 6. A shared challenge store for a scaled-out gate (#463)

**Question.** Where do the gate's per-call challenges live when more than one
instance serves the gate?

**Today.** `src/gate_challenges.py` keeps challenges in process, with a TTL and
a cap. Behind a load balancer, a challenge issued by one instance is unknown
to the next, and the turn is denied. That is safe, but it breaks the call. The
call-verification token store (`src/call_verification.py`) records the same
requirement.

**Recommended direction.**
- Use a DynamoDB table keyed by call id, holding the nonce and the expiry,
  with a native TTL.
- Issuing a challenge overwrites the call's previous one. Reads are strongly
  consistent, so the gate never accepts a replaced challenge.
- Use the same pattern as the call-verification redemption store, so one
  operational component serves both.
- Keep the in-process store for tests and single-instance demonstrations.

**Evidence that closes it:** two gate instances in a test, a challenge issued
on one and answered on the other, and a replaced challenge refused on both.

**May be said now:** "Challenges are held in process; a scaled-out deployment
needs a shared store."

## 7. NIST NCCoE project on agent identity and authorization (#464)

**Context.** The NCCoE published the concept paper *Accelerating the Adoption
of Software and Artificial Intelligence Agent Identity and Authorization* on
5 February 2026.
- It proposes a project applying existing identity standards to software and
  AI agents, among them OAuth, OpenID Connect, SCIM and SPIFFE.
- Its public comment period closed on 2 April 2026.

**What the project could offer:**
- the canonical scenario: an agent calls a payer, and the receiver must
  establish identity and authority before disclosure;
- Ida, as a worked example of an out-of-band, call-bound, scoped delegation
  with proof of possession;
- the evaluation corpora, as test material.

**Recommended direction.** Watch for the project's next step: a Federal
Register notice inviting collaborators, or a published project description.
If either appears, offer the scenario and the reference agent as input.

**Evidence that closes it:** a decision recorded either way, with the date and
what was sent.

**May be said now:** that the project is an independent research project and
reference implementation. Never imply NIST involvement, endorsement or
participation unless it is real and in writing.

---

## Sources

- [RFC 8693, OAuth 2.0 Token Exchange](https://www.rfc-editor.org/rfc/rfc8693)
- [draft-ietf-oauth-identity-chaining (IETF datatracker)](https://datatracker.ietf.org/doc/draft-ietf-oauth-identity-chaining/)
- [W3C Bitstring Status List v1.0, Recommendation, 15 May 2025](https://www.w3.org/TR/2025/REC-vc-bitstring-status-list-20250515/)
- [RFC 9795, PASSporT Extension for Rich Call Data](https://www.rfc-editor.org/rfc/rfc9795)
- [AWS KMS key spec reference](https://docs.aws.amazon.com/kms/latest/developerguide/symm-asymm-choose-key-spec.html)
- [45 CFR 164.514 (eCFR)](https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-C/part-164/subpart-E/section-164.514)
- [HHS: verification of identity, electronic (FAQ 569)](https://www.hhs.gov/hipaa/for-professionals/faq/569/how-may-hipaas-requirements-for-verification-of-identity-be-met-electronically/index.html)
- [NCCoE concept paper (PDF), February 2026](https://www.nccoe.nist.gov/sites/default/files/2026-02/accelerating-the-adoption-of-software-and-ai-agent-identity-and-authorization-concept-paper.pdf)
