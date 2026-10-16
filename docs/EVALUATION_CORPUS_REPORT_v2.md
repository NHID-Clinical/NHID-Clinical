# Governance Evaluation Corpus — Detection Report

<!-- GENERATED FILE — do not edit by hand.
     Regenerate with: python scripts/eval_corpus.py tests/evaluation_corpus_v2.json --report docs/EVALUATION_CORPUS_REPORT_v2.md --write-report
     Verified in CI by: python scripts/eval_corpus.py tests/evaluation_corpus_v2.json --report docs/EVALUATION_CORPUS_REPORT_v2.md --check -->

**Corpus**: `tests/evaluation_corpus_v2.json`  
**Scenarios**: 8 (2 compliant, 6 declaring violations)  
**Turns**: 20  
**Expected violations**: 10

This is a research measurement of one small hand-authored corpus. It is
not a conformance claim, a certification, an assurance score, or
independent validation.

## Detection

Measured only over scenarios that declare the violation in
`expected_violations`. A rule counts as detected if any turn in the
scenario surfaces it.

| Rule | Expected | Detected | Rate |
| :--- | ---: | ---: | ---: |
| ATR-01 | 1 | 0 | 0.0% |
| DBC-01 | 2 | 0 | 0.0% |
| EIT-01 | 1 | 1 | 100.0% |
| IDG-01 | 4 | 2 | 50.0% |
| PDX-01 | 2 | 2 | 100.0% |
| **OVERALL** | **10** | **5** | **50.0%** |

### Not detected

- **ATR-01** — `nhid_ec2_atr01_incomplete`
- **DBC-01** — `nhid_ec2_combo_contradiction_persona_late`, `nhid_ec2_combo_undisclosed_persona_phi`
- **IDG-01** — `nhid_ec2_combo_contradiction_persona_late`, `nhid_ec2_idg01_contradiction_crossturn`

## False positives

Measured over the disjoint population of compliant scenarios — those
declaring no expected violations. Anything they emit is a false positive.

- Compliant scenarios: **2**
- Emitting at least one violation: **0** (**0.0%**)

## Method and limits

- Detection and false positives are measured over **disjoint** scenario
  populations and must not be combined into one figure.
- Disclosure is carried forward across a scenario's turns
  (`carry_disclosure_forward`), because disclosure is a conversation-level
  fact. Without it every turn after the disclosing one reads as
  undisclosed. Detection figures are identical with and without it; a test
  pins that invariant.
- ATR-01 expectations in this corpus are not measurable in replay: the
  harness supplies the audit fields the rule checks. Its rate reflects the
  corpus, not the control.
- IDG-01's pass condition is that a disclosure timestamp is set and the
  assertion text is non-empty — **presence, not quality**. Scenarios that
  disclose with weak wording are counted as misses; that is a control-scope
  boundary, not a defect.
- This corpus is distinct from the Fabricate corpus (550 conversations,
  `scripts/confusion_matrix.py`) and the Tonic corpus (150 sessions,
  `scripts/evaluate_tonic_corpus.py`). Their figures are not interchangeable.
