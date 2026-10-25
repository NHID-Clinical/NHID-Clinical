# Canonical threat model and actor roles

**Scope of this document.** This is the *interaction* threat model: who is on the call,
whose information is at risk, and whose identity and authority must be established. It is
distinct from the "Threat Model" section of [`SECURITY.md`](SECURITY.md), which covers
the ATR-01 audit trail's assets and integrity — storage, tampering, key handling. Neither
supersedes the other; they describe different layers.

The same statement is carried in [`../CLAUDE.md`](../CLAUDE.md) so a tooling session
inherits it. `tests/test_canonical_threat_model.py` asserts the two do not drift apart.

---

## The scenario

**A caller-agent telephones a payer and asks for a patient's protected information.**

The **caller** is an agent that contacts a payer's customer service agent or medical
claims associate. It claims to be a healthcare provider, or to be acting on behalf of
one, and requests a patient's eligibility information, claim status or other protected
health information (PHI). Its identity and its authority to obtain the requested
information have not yet been sufficiently established.

The **receiving party** is the payer's customer service agent or medical claims
associate, who receives the request and must follow the applicable identity,
authorization and disclosure controls.

NHID-Clinical addresses the risk that the receiving party, or a connected workflow,
discloses PHI to an unverified or unauthorized requesting agent.

## The five actors

| Actor | Role |
| :-- | :-- |
| **Requesting caller-agent** | The party whose identity and authority must be established. Places the call. |
| **Receiving payer employee** | The customer service agent or medical claims associate handling the incoming request. |
| **Patient** | The person whose eligibility, claim status or PHI is being requested. Not necessarily participating in the call. |
| **Provider or represented organization** | The organization the caller claims to represent or act on behalf of. A claim of affiliation does not establish identity or delegated authority. |
| **Protected asset** | Patient eligibility information, claim status, and other applicable PHI. |

The roles are never reversed. The scenario is not a patient calling a voice agent, and
the agent under evaluation is not the party answering the phone — except where a separate
scenario is explicitly documented, which today means
[`payer-initiated-calls.md`](payer-initiated-calls.md) and nothing else.

## Control objective

Evaluate the requesting agent's identity and authority **before** permitting disclosure
of protected information.

- Identity disclosure is not identity verification.
- Identity verification is not authorization.
- A verified identity or an asserted provider affiliation does not, by itself, establish
  authority to receive the requested information.

When required checks are not satisfied, the existing policy outcome applies — denying
data access or escalating to a human. Logging an event, or disclosing identity, does not
authorize disclosure. No new control, outcome, metric or guarantee is introduced by this
document; it states the model the existing five controls were written against.

## How the roles appear in the artifacts

| Where | Caller-agent | Receiving payer employee |
| :-- | :-- | :-- |
| Policy engine event | `actor_id`, and `counterparty_type: human_operator` names what it is talking to | the `human_operator` counterparty |
| Tier 0 capture schema (`pilot-kit/minimal-event-schema.json`) | `speaker: "agent"` | `speaker: "caller"` — see the note below |
| `src/safety_evaluation/synthetic_scenarios.py` | `ParticipantRole.AI_AGENT` | `ParticipantRole.CLAIMS_REP` |
| Fabricate corpus | `agent_type: ai_voice_agent`, `caller_role` | not separately labelled |

### The `speaker: "caller"` naming

In the capture schema the agent under evaluation is `"agent"` and the payer-side human is
`"caller"` — which reads backwards, because the agent is the one placing the call. The
values are retained as they are: the schema ships in a downloaded kit and
`adapters/fabricate_adapter.py` and `src/pilot_measure.py` read them, so renaming would
break captures already in the field. Both values are now defined explicitly in the schema
rather than left to inference. `ParticipantRole` above is the unambiguous vocabulary
where a choice is available.

---

## Recorded conflict: `caller_role` in the Fabricate corpus

`fixtures/fabricate/conversations.csv` labels each conversation with a `caller_role`.
Measured over the committed 550:

| `caller_role` | n | Against the canonical model |
| :-- | --: | :-- |
| `provider_office_staff` | 141 | consistent |
| `member_representative` | 139 | **outside canonical scope** — a patient-side representative, not a provider or its agent |
| `prior_auth_coordinator` | 128 | consistent |
| `billing_specialist` | 107 | consistent |
| `payer_staff` | 35 | **inverts the direction** — the payer is the receiving party in this model, not the caller |

**This is flagged, not corrected.** The corpus is pinned baseline data
(`scripts/check_baseline.py`: IDG-01 70/70, PDX-01 41/41, DBC-01 183/200 with 5 FP,
EIT-01 169/171 with 5 FP). Rewriting those 174 rows would move a measured baseline and
falsify a corpus that was authored and evaluated as it stands.

What follows from it: detection and false-positive figures drawn from this corpus are
measured over a population that includes 174 conversations whose caller is not a provider
or a provider's agent. They remain valid measurements of the engine's behaviour on the
authored transcripts; they are not all measurements of the canonical scenario. Any claim
that narrows to the canonical scenario needs the subset, not the whole, and the subset has
not been separately evaluated.

---

*NHID-Clinical is an independent research project and reference implementation. Nothing
here claims production deployment, healthcare-provider adoption, HIPAA certification or
independent validation. See [`claim-boundaries.md`](claim-boundaries.md).*
