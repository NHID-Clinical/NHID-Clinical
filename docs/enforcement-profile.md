# Chapter 10 — Enforcement Profile

**Status:** Normative (NHID-Clinical v1.3). Documents behavior already implemented by the
deterministic policy engine. **This chapter adds no new control.** The framework remains four
behavioral controls (IDG-01, PDX-01, DBC-01, EIT-01) plus one audit requirement (ATR-01).

**Source of truth:** `src/nhid_policy_engine_v1.py` and the Conformance Test Suite
(`conformance/nhid_conformance_test_suite_v1.yaml`). Where this chapter and the reference
implementation disagree, the implementation and its `expected_policy_action` assertions win;
report the discrepancy.

**RFC 2119 note.** MUST / SHOULD / MAY define a voluntary, self-imposed conformance baseline.
They do not imply legal obligation. NHID-Clinical is a voluntary open proposal (CC BY 4.0) —
not an accredited standard, certification, or regulatory requirement.

---

## 10.1 Enforcement Profile

### 10.1.1 `PolicyDecision` — the output contract of control evaluation

Evaluating the five controls against a single call turn produces exactly one **`PolicyDecision`**.
It is the contract every receiver consumes. Its normative fields:

| Field | Meaning |
| :--- | :--- |
| `action` | The single `PolicyAction` the receiver MUST execute for this turn (§10.1.2). |
| `reason_code` | Stable machine token identifying which condition produced the action. |
| `violations[]` | Every `BoundaryViolation` (`rule_id`, `description`, `severity`) raised by **all** controls this turn — merged, never collapsed. |
| `next_state` | Advisory workflow state label. |
| `policy_version` | Engine version that produced the decision. |

A `PolicyDecision` carries **no score**. CAS is not a field of the decision and is computed
separately and downstream (§10.4).

### 10.1.2 `PolicyAction` vocabulary

There are exactly **five** actions. A sixth action MUST NOT be introduced (a new action would be
a sixth control in disguise). For each action:

| PolicyAction | Meaning | Receiver obligation | Affects PHI exchange? | Affects workflow state? |
| :--- | :--- | :--- | :--- | :--- |
| **`DISCLOSE_IDENTITY`** | The agent has not disclosed non-human identity. | Receiver MUST require identity disclosure before material interaction continues; MUST NOT treat the caller as verified. | **Yes** — material interaction is withheld until disclosure. | Yes → `AWAITING_DISCLOSURE`. |
| **`DENY_DATA`** | PHI exchange was attempted before disclosure (or an undisclosed agent-to-agent context). | Receiver MUST NOT request, accept, or release PHI on this turn. | **Yes** — PHI is blocked. | Yes → `GATE_BLOCKED`. |
| **`ESCALATE_HUMAN`** | A human handoff is required and either not honored or unavailable. | Receiver MUST provide a functional human escalation path. | Indirect — the interaction transfers to a human; automated exchange halts. | Yes → `ESCALATING` / `ESCALATION_FAILED`. |
| **`LOG_ONLY`** | A suggestive or evidentiary finding was raised (deceptive-behavior signal, or an audit-trail gap). | Receiver MUST record the finding; SHOULD route to human review per severity/CAS (§10.4). MUST NOT, by itself, treat this as a hard block. | **No** — not a data gate on its own. | No (state preserved / flagged, e.g. `DECEPTION_FLAGGED`). |
| **`CONTINUE_AI`** | The evaluated control(s) passed. | None beyond proceeding; the AI agent MAY continue, subject to the other controls. | No block. | Typically → `DISCLOSED` / `DATA_EXCHANGE_AUTHORIZED` / unchanged. |

> **Note (documented behavior, not a new rule):** DBC-01 emits `LOG_ONLY` for both a Tier-A
> artifact (CRITICAL severity) and a Tier-B/C text signal (MAJOR). A deception finding is therefore
> **recorded and routed**, not itself a PHI gate; any blocking on a deceptive turn arises from a
> co-occurring IDG-01/PDX-01 failure, resolved by the ladder in §10.2. The CRITICAL severity still
> propagates in `violations[]` and SHOULD drive review routing.

---

## 10.2 Enforcement Ladder

A single turn MAY trip multiple controls at once, but the receiver needs **one unambiguous
action**. When control outcomes conflict, the receiver MUST apply the most-protective action by
this fixed precedence:

```
DENY_DATA  >  ESCALATE_HUMAN  >  DISCLOSE_IDENTITY  >  LOG_ONLY  >  CONTINUE_AI
```

- **Why conflict resolution exists:** enforcement acts per turn; two controls can each demand a
  different response (e.g. PHI-before-disclosure *and* an unmet escalation request). The ladder
  guarantees a deterministic, safety-first selection: the action that most limits data exposure
  wins.
- **The ladder resolves outcomes; it does not replace evaluation.** Every control still evaluates
  independently and contributes its `violations[]`. The ladder only selects which single `action`
  the receiver executes — it never suppresses a control's findings, and it never re-decides
  conformance.

---

## 10.3 Consequence Matrix

Normative mapping of control outcome → `PolicyAction` → receiver obligation. Each obligation
attaches to an **existing** control — there is no standalone enforcement control.

| Control outcome | PolicyAction | Receiver obligation (normative) |
| :--- | :--- | :--- |
| **IDG-01** — no non-human disclosure | `DISCLOSE_IDENTITY` | Receiver MUST require identity disclosure before material interaction. |
| **PDX-01** — PHI attempted before disclosure | `DENY_DATA` | Receiver MUST prevent PHI exchange until disclosure is confirmed. |
| **EIT-01** — escalation unmet / no path | `ESCALATE_HUMAN` | Receiver MUST provide a functional human escalation path. |
| **DBC-01** — deceptive artifact or implied-human framing | `LOG_ONLY` | Receiver MUST record the finding and SHOULD route to human review per severity/CAS. |
| **ATR-01** — required audit field missing | `LOG_ONLY` | Receiver MUST preserve evidence and record the audit-trail gap. |
| All controls pass | `CONTINUE_AI` | Receiver MAY allow the AI agent to proceed. |

---

## 10.4 CAS Authority Boundary

The Call Authorization Score (CAS) is a **downstream assessment and routing** mechanism. It is
derived **after**, and **from**, the `PolicyDecision` (and audit-field completeness). It is not an
evaluator and not an enforcer.

**CAS MAY:**
- trigger human review (reference threshold: CAS below Conditional Trust, `0.75`);
- influence review priority and queueing.

**CAS MUST NOT:**
- override or modify a `PolicyDecision`;
- convert `DENY_DATA` (or any restrictive action) into allowed access;
- independently determine control compliance.

### Governing invariant (normative)

> The Enforcement Profile SHALL consume `PolicyDecision` outputs and SHALL NOT independently
> evaluate control conformance or modify the outcome of the five core controls. CAS SHALL be
> derived from, and downstream of, the `PolicyDecision`; it MAY drive review routing but SHALL NOT
> alter the emitted `PolicyAction`. The five controls remain the sole source of conformance
> decisions.

---

## Appendix 10.A — Normative vs. Reference-Implementation

To keep the specification portable, the following separation is normative.

**Normative (an independent implementation MUST reproduce):**
- the five control outcomes and their pass/fail conditions;
- the `PolicyAction` vocabulary and each action's meaning + receiver obligation (§10.1.2);
- the Enforcement Ladder precedence (§10.2);
- the Consequence Matrix receiver obligations (§10.3);
- the CAS authority boundary and governing invariant (§10.4);
- the ATR-01 required audit-field set (evidence requirement).

**Reference implementation only (informative — an implementation MAY differ):**
- the specific heuristic lexicons and their tuning (e.g. `_DBC_*` phrase lists,
  `_ESCALATION_TRIGGERS`, PHI-speech patterns);
- exact CAS scoring internals (NOCF/ECF weights and formula) beyond the tier thresholds;
- TwiML / audio fallback strings and prompt wording;
- internal `next_state` label spellings and `reason_code` string values;
- internal-error handling and the `LOG_ONLY` safe-default.

Implementers MUST NOT treat the reference lexicons or scoring internals as conformance
requirements; conformance is defined by control outcomes, actions, precedence, obligations, and
evidence — not by any particular phrase list or weight.
