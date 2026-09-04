#!/usr/bin/env python3
"""
Evaluate detection rates on the Governance Evaluation Corpus.

Reports two things, kept strictly separate because conflating them is how the
project ended up publishing an unsupported figure:

  * **Detection** — of the violations a scenario declares in
    `expected_violations`, how many did the engine surface. Measured over the
    20 scenarios that declare one.
  * **False positives** — of the compliant scenarios (those declaring no
    expected violations), how many emitted a violation anyway. Measured over
    the disjoint population of 5 compliant scenarios.

Before this script computed the second number, "0% false-positive rate" was
published against this corpus with nothing behind it. It is reported here so
the claim has a source, whatever the source says.

The generated report is the authoritative published surface for these
figures. It is emitted from the same run that computes them, never hand-written
— the previous report was prose, and when a scenario was added its per-rule
IDG-01 line went stale and then the file was deleted, leaving the only correct
copy of the number gone.

Usage:
    python scripts/eval_corpus.py [corpus.json]
    python scripts/eval_corpus.py --write-report    # regenerate the report
    python scripts/eval_corpus.py --check           # fail if the report is stale
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.nhid_policy_engine_v1 import evaluate_all
from src.synthetic_eval_loop import (
    build_event,
    build_session,
    carry_disclosure_forward,
    extract_rule_ids,
)

SCENARIO_TYPES = ["compliant_scenarios", "single_rule_violations", "multi_rule_combinations"]

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CORPUS = ROOT / "tests" / "evaluation_corpus_v1.json"
REPORT = ROOT / "docs" / "EVALUATION_CORPUS_REPORT_v1.md"


def load_corpus(path):
    """Load evaluation corpus (structured with metadata + scenario types)."""
    with open(path) as f:
        return json.load(f)


def evaluate_scenario(scenario_id, turns):
    """Evaluate all turns in a scenario and collect detected violations."""
    detected = set()

    # Disclosure is a conversation-level fact, not a per-turn one. Without this
    # every turn after the disclosing one looks undisclosed and the compliant
    # scenarios all report IDG-01/PDX-01. See carry_disclosure_forward().
    for i, turn in enumerate(carry_disclosure_forward(turns)):
        try:
            session = build_session(turn)
            event = build_event(scenario_id, i, turn)
            decision = evaluate_all(session, event)
            detected.update(extract_rule_ids(decision.violations))
        except Exception as e:
            print(f"Error evaluating turn {i}: {e}")

    return detected


def collect_scenarios(corpus):
    """Flatten the corpus's three scenario groups into one list."""
    scenarios = []
    for scenario_type in SCENARIO_TYPES:
        scenarios.extend(corpus.get(scenario_type, []))
    return scenarios


def evaluate_corpus(scenarios):
    """
    Run every scenario and return (detection_stats, false_positives, unexpected).

    `false_positives` maps each compliant scenario's id to the sorted rule ids
    it emitted — an empty list means that scenario is clean.

    `unexpected` maps each *violation* scenario's id to rules it emitted that
    the scenario did not declare. This was invisible until 2026-09-03, and the
    gap mattered: the published false-positive figure is measured only over the
    five compliant scenarios, so a rule firing where it was not expected on any
    of the other twenty could not show up in any number the project reported.
    There were eight such detections before this run and none of them were
    known. It is reported separately rather than folded into the
    false-positive rate, because the two are different quantities: a compliant
    scenario emitting anything is a defect, whereas a violation scenario
    emitting an undeclared rule is usually the corpus under-specifying what a
    turn contains. Judging which requires reading the scenario, so the number
    is surfaced and not interpreted.
    """
    stats = {}
    false_positives = {}
    unexpected = {}

    for scenario in scenarios:
        scenario_id = scenario.get("scenario_id", "unknown")
        expected_violations = set(scenario.get("expected_violations") or [])
        turns = scenario.get("turns", [])

        detected_violations = evaluate_scenario(scenario_id, turns)

        if not expected_violations:
            # A compliant scenario. Anything it emits is a false positive, and
            # it contributes nothing to the detection denominators.
            false_positives[scenario_id] = sorted(detected_violations)
            continue

        extra = sorted(detected_violations - expected_violations)
        if extra:
            unexpected[scenario_id] = extra

        for rule_id in expected_violations:
            bucket = stats.setdefault(rule_id, {"expected": 0, "detected": 0, "missed": []})
            bucket["expected"] += 1
            if rule_id in detected_violations:
                bucket["detected"] += 1
            else:
                bucket["missed"].append(scenario_id)

    for bucket in stats.values():
        bucket["detection_rate"] = (
            bucket["detected"] / bucket["expected"] if bucket["expected"] else 0.0
        )

    return stats, false_positives, unexpected


# G3, decided 2026-09-04. The five controls do not all live at the same layer,
# and a transcript-replay harness can only observe one of those layers.
#
# IDG-01, PDX-01, DBC-01 and EIT-01 are *behavioural*: what was said, in what
# order. A transcript is exactly the right evidence for them.
#
# ATR-01 is *audit/evidence*: it validates that required fields are present on
# the audit event record. A transcript is not an audit record. The normative
# conformance case ATR-01-FAIL-MISSING makes the layer explicit — it does not
# supply a transcript missing anything, it nulls `session_id` and
# `execution_context.pipeline_version` on the event object via
# `input_event_overrides`. Replayed from speech, ATR-01 cannot fail here,
# because build_event() constructs a complete, well-formed event from any turn.
#
# The scenario is NOT dropped and the denominator is NOT reduced — that would
# raise the headline rate by removing an inconvenient miss. Both figures are
# printed instead: the whole-corpus rate stays the headline, and the
# transcript-observable rate says what the replay harness can actually measure.
TRANSCRIPT_OBSERVABLE = ("IDG-01", "PDX-01", "DBC-01", "EIT-01")
AUDIT_EVIDENCE = ("ATR-01",)


def print_detection(stats):
    print("\n" + "="*60)
    print("EVALUATION CORPUS DETECTION RATES")
    print("="*60)
    print(f"{'Rule':<12} {'Expected':>10} {'Detected':>10} {'Rate':>10}")
    print("-"*60)

    total_expected = 0
    total_detected = 0
    obs_expected = 0
    obs_detected = 0

    for rule_id in sorted(stats.keys()):
        bucket = stats[rule_id]
        rate = bucket["detection_rate"]
        layer = "" if rule_id in TRANSCRIPT_OBSERVABLE else "  (audit/evidence)"
        print(f"{rule_id:<12} {bucket['expected']:>10} {bucket['detected']:>10} {rate:>9.1%}{layer}")
        total_expected += bucket["expected"]
        total_detected += bucket["detected"]
        if rule_id in TRANSCRIPT_OBSERVABLE:
            obs_expected += bucket["expected"]
            obs_detected += bucket["detected"]

    print("-"*60)
    if total_expected:
        overall_rate = total_detected / total_expected
        print(f"{'OVERALL':<12} {total_expected:>10} {total_detected:>10} {overall_rate:>9.1%}")
    print("="*60)

    if obs_expected and obs_expected != total_expected:
        obs_rate = obs_detected / obs_expected
        audit_expected = total_expected - obs_expected
        print()
        print("Measurement layers (G3) — the OVERALL figure above remains the")
        print("headline; neither layer replaces it, and no scenario is excluded.")
        print(f"  transcript-observable (IDG-01, PDX-01, DBC-01, EIT-01): "
              f"{obs_detected}/{obs_expected} = {obs_rate:.1%}")
        print(f"  audit/evidence (ATR-01): {total_detected - obs_detected}/{audit_expected} "
              f"— not measurable from transcripts; validated instead by")
        print("    tests/test_atr01_audit_trail.py, tests/test_atr01_persistence.py,")
        print("    tests/test_audit_integrity.py and the ATR-01 conformance pair.")


def print_unexpected(unexpected):
    """Rules fired on violation scenarios that did not declare them.

    Not folded into the false-positive rate: see evaluate_corpus().
    """
    total = sum(len(v) for v in unexpected.values())
    print("\n" + "=" * 60)
    print("UNEXPECTED DETECTIONS (violation scenarios only)")
    print("=" * 60)
    if not unexpected:
        print("None.")
    else:
        for sid in sorted(unexpected):
            print(f"  {sid}: {', '.join(unexpected[sid])}")
    print("-" * 60)
    print(f"Total: {total}")
    print("Reported separately from the false-positive rate, which is measured")
    print("only over compliant scenarios and cannot see any of these.")
    print("=" * 60)


def print_false_positives(false_positives):
    clean_total = len(false_positives)
    dirty = {sid: rules for sid, rules in false_positives.items() if rules}

    print("\n" + "="*60)
    print("FALSE POSITIVES (compliant scenarios only)")
    print("="*60)
    if not clean_total:
        print("No compliant scenarios in this corpus — false-positive rate not measurable.")
        print("="*60 + "\n")
        return

    print(f"Compliant scenarios: {clean_total}")
    print(f"Emitting >= 1 violation: {len(dirty)}  ({len(dirty)/clean_total:.1%})")

    per_rule = {}
    for rules in false_positives.values():
        for rule_id in rules:
            per_rule[rule_id] = per_rule.get(rule_id, 0) + 1

    if per_rule:
        print("-"*60)
        print(f"{'Rule':<12} {'Scenarios':>10} {'FP rate':>10}")
        for rule_id in sorted(per_rule):
            n = per_rule[rule_id]
            print(f"{rule_id:<12} {n:>10} {n/clean_total:>9.1%}")
        print("-"*60)
        for sid, rules in sorted(dirty.items()):
            print(f"  {sid}: {', '.join(rules)}")
    print("="*60 + "\n")


def build_report(corpus_path, scenarios, stats, false_positives, unexpected):
    """
    Render the corpus report as Markdown.

    Deterministic: no build timestamp, so regenerating an unchanged corpus
    produces a byte-identical file and `--check` is meaningful.
    """
    total_expected = sum(b["expected"] for b in stats.values())
    total_detected = sum(b["detected"] for b in stats.values())
    n_turns = sum(len(s.get("turns", [])) for s in scenarios)
    clean = list(false_positives)
    dirty = {sid: r for sid, r in false_positives.items() if r}

    L = [
        "# Governance Evaluation Corpus — Detection Report",
        "",
        "<!-- GENERATED FILE — do not edit by hand.",
        "     Regenerate with: python scripts/eval_corpus.py --write-report",
        "     Verified in CI by: python scripts/eval_corpus.py --check -->",
        "",
        f"**Corpus**: `{corpus_path}`  ",
        f"**Scenarios**: {len(scenarios)} ({len(clean)} compliant, "
        f"{len(scenarios) - len(clean)} declaring violations)  ",
        f"**Turns**: {n_turns}  ",
        f"**Expected violations**: {total_expected}",
        "",
        "This is a research measurement of one small hand-authored corpus. It is",
        "not a conformance claim, a certification, an assurance score, or",
        "independent validation.",
        "",
        "## Detection",
        "",
        "Measured only over scenarios that declare the violation in",
        "`expected_violations`. A rule counts as detected if any turn in the",
        "scenario surfaces it.",
        "",
        "| Rule | Expected | Detected | Rate |",
        "| :--- | ---: | ---: | ---: |",
    ]
    for rule_id in sorted(stats):
        b = stats[rule_id]
        L.append(f"| {rule_id} | {b['expected']} | {b['detected']} | {b['detection_rate']:.1%} |")
    if total_expected:
        L.append(f"| **OVERALL** | **{total_expected}** | **{total_detected}** | "
                 f"**{total_detected / total_expected:.1%}** |")

    misses = {r: b["missed"] for r, b in stats.items() if b["missed"]}
    if misses:
        L += ["", "### Not detected", ""]
        for rule_id in sorted(misses):
            L.append(f"- **{rule_id}** — {', '.join(f'`{m}`' for m in sorted(misses[rule_id]))}")

    L += [
        "",
        "## False positives",
        "",
        "Measured over the disjoint population of compliant scenarios — those",
        "declaring no expected violations. Anything they emit is a false positive.",
        "",
    ]
    if not clean:
        L.append("No compliant scenarios in this corpus; not measurable.")
    else:
        L += [
            f"- Compliant scenarios: **{len(clean)}**",
            f"- Emitting at least one violation: **{len(dirty)}** "
            f"(**{len(dirty) / len(clean):.1%}**)",
        ]
        per_rule = {}
        for rules in false_positives.values():
            for rule_id in rules:
                per_rule[rule_id] = per_rule.get(rule_id, 0) + 1
        if per_rule:
            L += ["", "| Rule | Scenarios | FP rate |", "| :--- | ---: | ---: |"]
            for rule_id in sorted(per_rule):
                n = per_rule[rule_id]
                L.append(f"| {rule_id} | {n} | {n / len(clean):.1%} |")
            L += ["", "Affected scenarios:", ""]
            for sid, rules in sorted(dirty.items()):
                L.append(f"- `{sid}` — {', '.join(rules)}")

    L += [
        "",
        "## Method and limits",
        "",
        "- Detection and false positives are measured over **disjoint** scenario",
        "  populations and must not be combined into one figure.",
        "- Disclosure is carried forward across a scenario's turns",
        "  (`carry_disclosure_forward`), because disclosure is a conversation-level",
        "  fact. Without it every turn after the disclosing one reads as",
        "  undisclosed. Detection figures are identical with and without it; a test",
        "  pins that invariant.",
        "- ATR-01 expectations in this corpus are not measurable in replay: the",
        "  harness supplies the audit fields the rule checks. Its rate reflects the",
        "  corpus, not the control.",
        "- IDG-01's pass condition is that a disclosure timestamp is set and the",
        "  assertion text is non-empty — **presence, not quality**. Scenarios that",
        "  disclose with weak wording are counted as misses; that is a control-scope",
        "  boundary, not a defect.",
        "- This corpus is distinct from the Fabricate corpus (550 conversations,",
        "  `scripts/confusion_matrix.py`) and the Tonic corpus (150 sessions,",
        "  `scripts/evaluate_tonic_corpus.py`). Their figures are not interchangeable.",
        "",
    ]
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Evaluate the Governance Evaluation Corpus.")
    ap.add_argument("corpus", nargs="?", default=str(DEFAULT_CORPUS))
    ap.add_argument("--write-report", action="store_true",
                    help=f"regenerate {REPORT.relative_to(ROOT)}")
    ap.add_argument("--check", action="store_true",
                    help="fail if the report is missing or stale; write nothing")
    args = ap.parse_args(argv)

    corpus_path = Path(args.corpus)
    if not corpus_path.exists():
        print(f"Corpus not found: {corpus_path}", file=sys.stderr)
        return 1

    corpus = load_corpus(corpus_path)
    scenarios = collect_scenarios(corpus)
    stats, false_positives, unexpected = evaluate_corpus(scenarios)

    try:
        rel = corpus_path.resolve().relative_to(ROOT)
    except ValueError:
        rel = corpus_path
    report = build_report(rel, scenarios, stats, false_positives, unexpected)

    if args.check:
        if not REPORT.exists():
            print(f"CORPUS REPORT FAIL: {REPORT.relative_to(ROOT)} does not exist. "
                  "Run scripts/eval_corpus.py --write-report.", file=sys.stderr)
            return 1
        if REPORT.read_text(encoding="utf-8") != report:
            print(f"CORPUS REPORT FAIL: {REPORT.relative_to(ROOT)} is stale. "
                  "Run scripts/eval_corpus.py --write-report and commit the result.",
                  file=sys.stderr)
            return 1
        print(f"CORPUS REPORT PASS: {REPORT.relative_to(ROOT)} matches the measured corpus")
        return 0

    if args.write_report:
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(report, encoding="utf-8")
        print(f"Wrote {REPORT.relative_to(ROOT)}")

    print(f"\nCorpus: {rel}")
    print(f"Scenarios: {len(scenarios)}   Turns: "
          f"{sum(len(s.get('turns', [])) for s in scenarios)}")
    print_detection(stats)
    print_false_positives(false_positives)
    print_unexpected(unexpected)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
