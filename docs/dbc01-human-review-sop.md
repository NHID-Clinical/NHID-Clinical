## DBC-01 Human-Review SOP (Updated June 2026)

**Status:** Operationalized for pilots

## Reality Check
Pure keyword matching on `_DBC_IMPERSONATION_PHRASES` has a hard ceiling. Expanding the list creates excessive false positives (proven via mining script on full Fabricate corpus). Most deceptive behavior is implicit (ownership language, reassurance without disclosure). We accept this limit and design around it.

**Goal:** Reliable flagging + human judgment workflow, not 95% automated detection.

## Triggers for Human Review Queue
Route to review when **any** hold:

1. **Phrase match** — `evaluate_dbc01()` returns `LOG_ONLY` + `MAJOR` severity (`DBC01_IMPERSONATION_PHRASE_DETECTED`).
2. **Low CAS trust** — CAS tier `Review Required` or worse (`cas < 0.75`).
3. **Ownership pattern (modest new heuristic)** — Heavy first-person ownership language ("I’ll personally handle", "my team has reviewed", "I’m taking care of this") in context of PHI activity **without** clear prior disclosure. Implement as optional multi-turn check.

**Do NOT trigger on:** Benign escalation mentions or clean calls.

## Reviewer Procedure
1. Pull full trace (including `identity_assertion_text` and CAS breakdown).
2. Judge in full conversation context.
3. Confirmed impersonation → escalate per org incident process.
4. False positive / ambiguous → document pattern; do **not** ad-hoc add phrases.

## New Phrase Candidates
Always run through `scripts/mine_heuristic_candidate.py` first. Zero false positives only.

## Policy & CAS Integration
- Keep DBC-01 mostly `LOG_ONLY` (non-blocking).
- Increase CAS penalty weight for DBC-01 violations.
- Document limitation honestly in specs/README.

**Honest Target:** Strong flagging + review process. This is more valuable than fragile high automation.

---

*This SOP formalizes the human review path recommended in the project archive.*