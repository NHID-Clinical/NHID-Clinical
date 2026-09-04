# Governance Evaluation Corpus — Detection Report

<!-- GENERATED FILE — do not edit by hand.
     Regenerate with: python scripts/eval_corpus.py --write-report
     Verified in CI by: python scripts/eval_corpus.py --check -->

**Corpus**: `tests/evaluation_corpus_v1.json`  
**Scenarios**: 25 (5 compliant, 20 declaring violations)  
**Turns**: 55  
**Expected violations**: 32

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
| DBC-01 | 9 | 9 | 100.0% |
| EIT-01 | 8 | 8 | 100.0% |
| IDG-01 | 8 | 7 | 87.5% |
| PDX-01 | 6 | 6 | 100.0% |
| **OVERALL** | **32** | **30** | **93.8%** |

### Not detected

- **ATR-01** — `nhid_ec_atr01_001`
- **IDG-01** — `nhid_ec_idg01_003`

## False positives

Measured over the disjoint population of compliant scenarios — those
declaring no expected violations. Anything they emit is a false positive.

- Compliant scenarios: **5**
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
