# Governance Evaluation Corpus — remediation record

**Measured 2026-09-03.** Kept strictly separate from the conformance suite: this
is a research measurement of whether the engine detects governance conditions,
not a pass/fail gate. Conformance-test pass rate, governance detection rate,
false-positive rate, scenario count and control count are five different
numbers and none of them substitutes for another.

| | Before | After |
|---|---|---|
| Detection | 29/32 = **90.6%** | 29/32 = **90.6%** — unchanged |
| False positives (5 compliant scenarios) | 0/5 = **0.0%** | 0/5 = **0.0%** |
| Unexpected detections (20 violation scenarios) | **8, unmeasured** | **8, now measured and reported** |
| Corpus scenarios / turns | 25 / 55 | 25 / 55 — **unchanged** |
| Engine logic | — | **unchanged** |

**The 98–99% target was not reached, and nothing was done to make the number
say otherwise.** Measured detection is **90.6%**. The one change shipped is a
*measurement* improvement, not a detection one: an entire class of engine
behaviour was previously invisible to every published figure (§1).

**Nothing was manipulated.** `tests/evaluation_corpus_v1.json` is byte-identical
to its prior state — no scenario added, removed, relabelled, reworded, excluded,
or re-declared. The engine is byte-identical too. The Fabricate baseline is
unchanged and verified (§6).

**An engine fix was attempted and deliberately reverted.** §2.1 records it in
full, because the reason it was withdrawn is the most useful finding here.

---

## 1. The finding that matters more than the rate

The published false-positive figure is measured **only over the five compliant
scenarios**. It therefore cannot see a rule firing where it was not expected on
any of the other twenty.

**There were eight such detections, and none of them were known.** They had
never appeared in any number the project reported, because no number looked
there.

This is now measured and printed on every run as a separate quantity
(`UNEXPECTED DETECTIONS`), and deliberately **not** folded into the
false-positive rate. The two are different things:

- a **compliant** scenario emitting anything is a defect in the engine;
- a **violation** scenario emitting an undeclared rule is usually the corpus
  under-specifying what its own turns contain.

Judging which requires reading the scenario, so the count is surfaced and left
uninterpreted by the tooling.

---

## 2. The three misses, classified

### 2.1 `nhid_ec_idg01_002` — "Vague Disclosure (Generic System)" · **ATTEMPTED, REVERTED**

| | |
|---|---|
| **Assertion** | `"claims system"` — *"You've reached the claims system. Can I have your member ID?"* |
| **Expected** | IDG-01 |
| **Detected** | PDX-01 only |
| **Apparent cause** | IDG-01 accepts any non-empty `identity_assertion_text` unless it introduces a *human persona*. Naming a system claims no persona, so it passes — while disclosing nothing. |

**The fix that was written.** Require the disclosing turn to *affirmatively*
assert non-human identity, subsuming the persona-only check. It worked: detection
went 29/32 → 30/32, the Fabricate baseline was untouched, and compliant-scenario
false positives stayed at zero. It also generalised to four further scenarios of
the same shape rather than special-casing one string.

**Why it was reverted.** It broke a pre-existing test that exists precisely to
forbid it — `test_bare_organisational_names_are_out_of_scope`, whose docstring
reads:

> *Deliberately NOT flagged. The corpus labels 'claims system' a violation and
> 'authorization system' compliant; no rule separates them, so the engine does
> not try.*

That is a **prior, deliberate, documented decision to abstain**, taken because
the corpus is self-contradictory on this exact shape, and locked with a test so
it could not be undone by accident. The mechanism worked: it caught this.

Shipping the change would have meant overturning a recorded decision on the
strength of one scenario, and keeping it green would have meant deleting a test
because it failed. Both were ruled out. The engine was restored to its committed
state.

**This miss is therefore not an engine defect.** It is the visible consequence of
an unresolved contradiction *inside the corpus*, which is item **G2** in §5. The
engine is not wrong to abstain; the corpus has not said what the right answer is.

### 2.2 `nhid_ec_idg01_003` — "Borderline AI Language" · **NOT FIXED — UNKNOWN**

| | |
|---|---|
| **Assertion** | `"I'm an automated assistant"` |
| **Expected** | IDG-01 (the corpus treats this as too weak, lacking an explicit "AI" claim) |
| **Cause** | **The expectation contradicts the canonical specification and the engine's own remediation text.** |

Two pieces of repository evidence point the same way:

1. The canonical control is *"Agent MUST identify itself as **automated**"* —
   which `"I'm an automated assistant"` does, literally.
2. The engine's own IDG-01 remediation TwiML is *"Hello. I am an **automated
   system**. I am not a human representative."* Flagging this assertion would
   make the engine's prescribed fix itself a violation.

Making the engine reject it would therefore require the engine to contradict
both the specification and its own remediation. **No change was made in either
the engine or the corpus.** Whether NHID-Clinical requires the literal word
"AI", or accepts "automated", is a specification decision for a person.

### 2.3 `nhid_ec_atr01_001` — "Missing Audit Event" · **NOT FIXABLE ON THIS PATH**

| | |
|---|---|
| **Expected** | ATR-01 |
| **Cause** | **Methodology limit, already documented.** `docs/EVALUATION_CORPUS_REPORT_v1.md` records that ATR-01 expectations in this corpus are not measurable in replay. |

ATR-01 validates that required fields are present **on the audit event record**.
The harness's `build_event()` constructs a complete, well-formed event —
`event_id`, `timestamp`, `session_id`, `request_id`, `actor_id`, and a full
`execution_context` — from any turn, regardless of what the scenario omits. The
scenario expresses its intent by leaving fields out of turn 1; the builder puts
them back.

Nor would a faithful builder help: the fields turn 1 omits (`disclosure_timestamp`,
`identity_assertion_text`) are **governance** fields, not the audit fields ATR-01
checks — and `carry_disclosure_forward()` correctly propagates the disclosure
from turn 0 anyway, because disclosure is a conversation-level fact.

**No ATR-01 detection was manufactured.** Doing so would have meant weakening
the audit-completeness check or special-casing the corpus. ATR-01 is genuinely
exercised elsewhere — 21 offline tests plus its own implementation suite — just
not through transcript replay.

---

## 3. The eight unexpected detections

None were introduced by this work; all eight pre-date it and none had ever been
reported. Read individually, all eight look like **correct detections against
scenarios that under-declare what their turns contain**:

| Scenario | Undeclared rule fired | Why it looks correct |
|---|---|---|
| `nhid_ec_idg01_001/002/003`, `nhid_ec_combo_005` | PDX-01 | A protected-data request made in the same turn as the initial disclosure. The engine holds that disclosure must precede the request as a distinct turn |
| `nhid_ec_pdx01_001` | IDG-01 | Turn 0 carries **no disclosure at all**. The scenario is about PHI before disclosure, so IDG-01 firing is the point |
| `nhid_ec_dbc01_001/002`, `nhid_ec_combo_003` | IDG-01 | Human personas — *"I'm Representative Alex from claims"*, *"I'm a specialist"*, *"I'm Taylor with Authorization Services"* — with no non-human assertion |

**No scenario was edited to declare them.** Adding these to `expected_violations`
would raise the reported detection rate, which is exactly the move that must not
be made to approach a target. They are recorded as **G2** in §5 for a person to rule on.

## 4. Why 90.6%, and what would move it

All three misses are blocked on decisions rather than on code:

| Miss | Blocked on |
|---|---|
| `nhid_ec_idg01_002` | A corpus contradiction the engine deliberately abstains from (§2.1, G2) |
| `nhid_ec_idg01_003` | Whether IDG-01 requires the literal word "AI" (§2.2, G1) |
| `nhid_ec_atr01_001` | ATR-01 is not observable through transcript replay (§2.3, G3) |

Reaching 98–99% from here would require editing the corpus, relaxing a control,
overturning a documented decision, or deleting a test. All four were available.
None was taken.

**Measured result: 90.6% detection · 0.0% false positives on compliant scenarios
· 8 unexpected detections, reported separately.**

## 5. Open items requiring human judgment

| # | Question | Why it cannot be settled from repository evidence |
|---|---|---|
| G1 | Does IDG-01 require the literal word "AI", or is "automated" sufficient? | The specification says "automated"; the corpus expects stricter. Both are internally coherent; they disagree. Settling it changes `nhid_ec_idg01_003` and possibly the engine's remediation wording |
| G2 | Is a bare organisational name ("claims system", "authorization system") an IDG-01 violation? | **The corpus says both yes and no.** It declares `"claims system"` a violation and does not declare `"authorization system"` one, and the two are the same shape. Until that is settled the engine abstains, by an explicit prior decision (§2.1). Settling it closes `nhid_ec_idg01_002` and changes four other scenarios |
| G3 | Should ATR-01 be measurable from transcripts at all? | It validates the audit record, and a transcript is not one. Possibly the corpus should not carry ATR-01 expectations, or a different harness should evaluate them |
| G4 | Is a same-turn disclosure plus PHI request a PDX-01 violation? | The engine says yes and four scenarios disagree by omission. Defensible either way |

---

## 6. Fabricate baseline — unchanged, and verified

`scripts/check_baseline.py` reports **IDG-01 70/70 (0 FP), PDX-01 41/41 (0 FP),
DBC-01 183/200 (5 FP), EIT-01 169/171 (5 FP)** — identical throughout, including
during the attempted change in §2.1, which was scoped so the Fabricate replay
path never reached it. The fixtures are byte-identical to the anchor taken before
any of this work began:

```
47e8beee37c95763bc6ee6f3d049cb9e75a4b987297b4327bdea9a2416cd777e  fixtures/fabricate/conversations.csv
5117a4aab950255d34b40c7f23298b4e9c2e622b5a5b947caed3997a9c4b337d  fixtures/fabricate/turns.csv
```

---

## 7. Reproduce

```bash
python scripts/eval_corpus.py          # detection, false positives, unexpected
python scripts/check_baseline.py       # Fabricate baseline, must be unchanged
sha256sum fixtures/fabricate/*.csv     # must match the hashes above
git diff --stat tests/evaluation_corpus_v1.json src/nhid_policy_engine_v1.py  # must be empty
```
