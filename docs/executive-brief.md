# NHID-Clinical — Executive Brief

*A one-page overview for hospital, payer, compliance, and procurement leaders.*

NHID-Clinical is a voluntary governance control layer for AI voice agents on
healthcare payer–provider calls. It was built from direct payer operations
experience on live eligibility, claims, and prior-authorization lines. It is an
open framework — **not an accredited standard, certification, or regulatory
requirement.**

---

## The operational problem

AI voice agents now place and answer administrative calls between provider
offices and payers. On many of these calls the agent begins operating —
requesting member IDs, NPIs, dates of birth, and claim data — **before the
receiving party can confirm it is automated and authorized to act.**

That gap between "the agent is already talking" and "we know who and what it is"
is **impersonation latency.** It creates wasted handling time, inconsistent
disclosure, and audit blind spots on both sides of the call.

## What the control layer does

Five testable controls, plus a per-call score. Each is observable on a real call
and checkable against a machine-readable trace.

| Control | What it requires |
| :-- | :-- |
| **IDG-01** — Identity Disclosure Gate | Disclose non-human identity before any PHI is exchanged. |
| **PDX-01** — Pre-Data Exchange Gate | No protected data until identity is disclosed. |
| **DBC-01** — Deceptive Behavior Check | No synthetic human-presence cues or false human-status claims. |
| **EIT-01** — Escalation Implementation Test | A clear human handoff path, honored on request. |
| **ATR-01** — Audit Trail | Every call produces a machine-readable trace. |
| **CAS** — Call Authorization Score | A per-call score summarizing conformance across the controls. |

## What a pilot involves

A Tier 0 shadow pilot is **observe-only.** It runs on your own call logs, in
parallel with live traffic.

- **2–4 weeks**, no vendor changes, no production risk.
- You map a sample of your call records to a minimal event schema and run the
  measurement script.
- You get impersonation-latency and disclosure metrics on your own traffic, in a
  ready-to-share report.
- You use the results to decide what to require of vendors — nothing is imposed.

Start with the [Tier 0 Shadow Pilot Kit](pilot-kit/README.md).

## Current maturity (honest)

- **Available today:** deterministic policy engine with 1073 passing tests,
  pilot-ready infrastructure (cryptographic audit signing, persistent storage, Docker
  deployment, security monitoring), a live v1.3 conformance API, the Tier 0 Shadow Pilot Kit,
  and the NHID-Auth v2 cryptographic authorization layer as public reference code.
- **In progress:** first shadow-evaluation partners; expanded adapters.
- **Not yet:** production-scale deployments, a certification, or any regulatory
  endorsement.

## Contact

- Website: <https://nhid-clinical.org>
- For payers and evaluation teams: <https://nhid-clinical.org/shadow-evaluation-guide.html>
- Email: <contact@nhid-clinical.org>

CC BY 4.0 · Submitted as public comment to NIST (NIST-2025-0035-0026) — a public
comment, not a NIST endorsement, adoption, or certification.
