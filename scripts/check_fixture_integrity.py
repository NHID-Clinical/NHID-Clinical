#!/usr/bin/env python3
"""
NHID-Clinical – fixture self-consistency guard
==============================================
Checks that the committed evaluation corpora describe themselves accurately.
`scripts/check_baseline.py` pins per-control DETECTION RATES; nothing checked
the fixtures' own structure, so defects sat in committed data while CI reported
green:

  - `fixtures/fabricate/README.md` claimed "~2,200 turns" for a 4,838-row file.
  - `num_turns` disagreed with the actual row count in 42/550 fabricate
    conversations and 148/300 voice-stress scenarios; `num_assertions`
    disagreed in 300/300.
  - `turns.scenario_id` joins to `scenarios.id`, NOT to the identically-shaped
    `scenarios.scenario_id`. Joining on the latter returns zero rows with no
    error — a silent empty join.

Two kinds of check live here:

  1. INVARIANTS (`check_*` functions) that must hold unconditionally — unique
     primary keys, every child row resolving to a parent, the documented join
     column matching and the decoy column matching nothing.
  2. PINNED MEASUREMENTS (`EXPECTED_*` tables) frozen at their measured values.
     The stale vendor count columns are deliberately NOT corrected — the raw
     exports are preserved as shipped (same precedent as
     `fixtures/fabricate/staging/README.md`) — so their divergence is pinned
     instead. Documented staleness passes; NEW drift fails.

If a change legitimately moves a pinned number, update the table below in the
SAME commit and record it per docs/MASTER-KNOWLEDGE-ARCHIVE.md §9.1.

Usage:
  python scripts/check_fixture_integrity.py

Proving this guard is not blind
-------------------------------
A guard that narrows until it verifies less than its output claims has bitten
this repo four times (PDFs outside check_number_drift's WATCHED list; the
nightly shallow checkout; the \\d{3} count patterns that went blind when the
suite crossed 1000 tests; and the fixture defects above). So corrupt a COPY of
the fixtures and confirm a non-zero exit for each:

  import csv, pathlib, shutil, subprocess, sys, tempfile
  REPO = pathlib.Path(".").resolve()
  CASES = {
      "drop a turn row":        ("fixtures/fabricate/turns.csv", lambda rows: rows[:-1]),
      "repoint a join key":     ("fixtures/voice-stress/turns.csv",
                                 lambda rows: [{**rows[0], "scenario_id": "nope"}] + rows[1:]),
      "duplicate a key":        ("fixtures/voice-stress/scenarios.csv",
                                 lambda rows: rows + [rows[0]]),
      "flip a violation flag":  ("fixtures/fabricate/conversations.csv",
                                 lambda rows: [{**rows[0], "idg01_violation": "1"}] + rows[1:]),
  }
  for name, (rel, mutate) in CASES.items():
      with tempfile.TemporaryDirectory() as tmp:
          work = pathlib.Path(tmp) / "repo"
          shutil.copytree(REPO, work, ignore=shutil.ignore_patterns(".git"))
          target = work / rel
          rows = list(csv.DictReader(target.open(newline="", encoding="utf-8")))
          rows = mutate(rows)
          with target.open("w", newline="", encoding="utf-8") as fh:
              w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
              w.writeheader(); w.writerows(rows)
          rc = subprocess.run([sys.executable, "scripts/check_fixture_integrity.py"],
                              cwd=work, capture_output=True, text=True).returncode
          print(("DETECTED " if rc else "BLIND    ") + name)

Write the harness in Python, not sed: a sed field delimiter collided with the
pattern content when check_number_drift.py was tested this way and produced two
false "guard is blind" readings.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Table paths below are relative to this directory ("fabricate/turns.csv").
FIXTURES = REPO / "fixtures"

TRUTHY = {"1", "true", "yes", "y", "t"}

# ── Pinned measurements (verified 2026-10-19 at 77d1957) ─────────────────────

# Exact row counts. The fixture READMEs quote these; a corpus that grows or
# shrinks must update both in the same commit.
EXPECTED_ROWS = {
    "fabricate/conversations.csv": 550,
    "fabricate/turns.csv": 4838,
    "voice-stress/scenarios.csv": 300,
    "voice-stress/turns.csv": 1582,
    "voice-stress/assertions.csv": 2071,
}

# Known-stale vendor metadata, pinned rather than corrected:
#   (rows whose declared value is wrong, sum of declared values, actual rows)
EXPECTED_STALE = {
    ("fabricate/conversations.csv", "num_turns"): (42, 4796, 4838),
    ("voice-stress/scenarios.csv", "num_turns"): (148, 1782, 1582),
    ("voice-stress/scenarios.csv", "num_assertions"): (300, 806, 2071),
}

# Ground-truth violation labels in the fabricate corpus. These are the RAW
# column counts, before the adapter's documented exclusions (PDX-01 loses 29
# rows that disclose at turn 0; ATR-01 loses all 14 as untestable in replay),
# which is why PDX-01 reads 70 here and 41 in check_baseline.py.
EXPECTED_FABRICATE_LABELS = {
    "idg01_violation": 70,
    "pdx01_violation": 70,
    "dbc01_violation": 200,
    "eit01_violation": 171,
    "atr01_violation": 14,
}
EXPECTED_FABRICATE_SCENARIO_TYPES = {
    "adversarial": 333,
    "compliant": 127,
    "non_compliant": 90,
}

# Voice-stress scoreable population. `confusion_matrix.compute` can only score
# a scenario that declares an IDG/PDX/DBC/EIT expectation, so shrinking this
# set would quietly raise every rate.
EXPECTED_VOICE_STRESS_POPULATION = {
    "negative_controls": 95,
    "positives": 205,
    "positives_unscoreable": 87,
    "positives_scoreable": 118,
}
# Why each unscoreable positive cannot be scored, keyed by `expected_control`.
EXPECTED_UNSCOREABLE_REASONS = {
    "NHID-Auth (proposed, not an existing control)": 67,
    "ATR-01, NHID-Auth (proposed)": 10,
    "ATR-01": 5,
    "none": 5,
}

# Prose claims the fixture READMEs must carry. The "~2,200 turns" error in
# fixtures/fabricate/README.md survived because no guard read the files that
# state the corpora's own size. check_number_drift.py does not cover these: its
# COUNT_CLAIMS patterns are about passing-test counts, and its
# CORPUS_TURNS_CLAIM regex ("N scenarios, N turns") belongs to the 25-scenario
# governance corpus, so pointing it here would guard nothing and risk matching
# one corpus's figures against another's. The numbers are measured in this
# file, so the claim check lives here too.
README_CLAIMS = {
    "fixtures/fabricate/README.md": [
        "550 conversations, 4,838 turns",
        "42 of 550",
        "declared sum 4,796; actual 4,838",
    ],
    "fixtures/voice-stress/README.md": [
        "| `scenarios.csv` | 300 |",
        "| `turns.csv` | 1,582 |",
        "| `assertions.csv` | 2,071 |",
        "| `num_turns` | 148 / 300 | 1,782 | **1,582** |",
        "| `num_assertions` | 300 / 300 | 806 | **2,071** |",
    ],
}

CONTROL_FLAGS = {
    "IDG-01": "expected_idg01_violation",
    "PDX-01": "expected_pdx01_violation",
    "DBC-01": "expected_dbc01_violation",
    "EIT-01": "expected_eit01_violation",
    "ATR-01": "expected_atr01_violation",
}
CORE_FLAGS = [CONTROL_FLAGS[c] for c in ("IDG-01", "PDX-01", "DBC-01", "EIT-01")]


def truthy(value: str) -> bool:
    return value.strip().lower() in TRUTHY


def read(rel: str) -> list[dict[str, str]]:
    with (FIXTURES / rel).open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def check_row_counts(tables: dict[str, list[dict]], fail) -> None:
    for rel, expected in EXPECTED_ROWS.items():
        got = len(tables[rel])
        if got != expected:
            fail(f"{rel}: expected {expected} rows, got {got}")


def check_unique_keys(tables: dict[str, list[dict]], fail) -> None:
    for rel, rows in tables.items():
        ids = [r["id"] for r in rows]
        if len(set(ids)) != len(ids):
            dupes = {i for i in ids if ids.count(i) > 1}
            fail(f"{rel}: 'id' is not unique ({len(ids) - len(set(ids))} duplicates, "
                 f"e.g. {sorted(dupes)[:3]})")
        fingerprints = {tuple(sorted(r.items())) for r in rows}
        if len(fingerprints) != len(rows):
            fail(f"{rel}: {len(rows) - len(fingerprints)} fully duplicate row(s)")


def check_join(tables: dict[str, list[dict]], parent: str, child: str,
               child_key: str, decoy: str, fail) -> None:
    """The documented join must resolve completely; the decoy must resolve not at all.

    Asserting only "some column joins" would pass if the two columns were
    swapped, which is the mistake this check exists to make impossible.
    """
    parent_ids = {r["id"] for r in tables[parent]}
    decoy_values = {r[decoy] for r in tables[parent]}
    child_keys = {r[child_key] for r in tables[child]}

    orphans = child_keys - parent_ids
    if orphans:
        fail(f"{child}.{child_key}: {len(orphans)} value(s) do not resolve to "
             f"{parent}.id (e.g. {sorted(orphans)[:3]})")

    childless = parent_ids - child_keys
    if childless:
        fail(f"{parent}: {len(childless)} row(s) have no {child} rows "
             f"(e.g. {sorted(childless)[:3]})")

    overlap = child_keys & decoy_values
    if overlap:
        fail(f"{child}.{child_key} now matches {parent}.{decoy} on "
             f"{len(overlap)} value(s) — the documented join key is "
             f"{parent}.id and {decoy} is documented as matching nothing. "
             f"Update fixtures/*/README.md in the same commit.")


def check_declared_counts(tables: dict[str, list[dict]], parent: str,
                          child: str, child_key: str, column: str,
                          fail) -> None:
    """Pin the divergence of a stale declared-count column, don't require zero."""
    counts: dict[str, int] = {}
    for row in tables[child]:
        counts[row[child_key]] = counts.get(row[child_key], 0) + 1

    wrong = 0
    declared_sum = 0
    for row in tables[parent]:
        declared = int(row[column])
        declared_sum += declared
        if declared != counts.get(row["id"], 0):
            wrong += 1

    got = (wrong, declared_sum, len(tables[child]))
    expected = EXPECTED_STALE[(parent, column)]
    if got != expected:
        fail(f"{parent}.{column}: declared-vs-actual divergence moved — "
             f"expected {expected[0]} wrong row(s), declared sum {expected[1]}, "
             f"{expected[2]} actual; got {got[0]} wrong, declared sum {got[1]}, "
             f"{got[2]} actual")


def check_fabricate_labels(tables: dict[str, list[dict]], fail) -> None:
    rows = tables["fabricate/conversations.csv"]
    for column, expected in EXPECTED_FABRICATE_LABELS.items():
        got = sum(1 for r in rows if truthy(r[column]))
        if got != expected:
            fail(f"fabricate/conversations.csv: {column} positives moved — "
                 f"expected {expected}, got {got}")

    seen: dict[str, int] = {}
    for r in rows:
        seen[r["scenario_type"]] = seen.get(r["scenario_type"], 0) + 1
    if seen != EXPECTED_FABRICATE_SCENARIO_TYPES:
        fail(f"fabricate/conversations.csv: scenario_type distribution moved — "
             f"expected {EXPECTED_FABRICATE_SCENARIO_TYPES}, got {seen}")


def check_compliant_population_agrees(tables: dict[str, list[dict]], fail) -> None:
    """The false-positive denominator must mean the same thing in code and docs.

    `confusion_matrix.compute` measures false positives over conversations
    whose `scenario_type == "compliant"`. docs/project-state.md §11 describes
    that same population of 127 as "conversations with 0 on all five
    *_violation columns". The two definitions currently select the identical
    127 rows. If they diverged, every published FP rate would quietly change
    meaning while both the code and the doc still looked correct.
    """
    rows = tables["fabricate/conversations.csv"]
    by_type = {r["id"] for r in rows if r["scenario_type"] == "compliant"}
    by_label = {
        r["id"] for r in rows
        if not any(truthy(r[c]) for c in EXPECTED_FABRICATE_LABELS)
    }
    if by_type != by_label:
        only_type = sorted(by_type - by_label)[:3]
        only_label = sorted(by_label - by_type)[:3]
        fail(f"fabricate/conversations.csv: the false-positive denominator no "
             f"longer has one meaning — scenario_type=='compliant' selects "
             f"{len(by_type)} row(s), zero-on-all-five-violation-columns "
             f"selects {len(by_label)}. Only in scenario_type: {only_type}; "
             f"only in label: {only_label}. confusion_matrix.py uses the "
             f"former, docs/project-state.md §11 documents the latter.")


def check_voice_stress_labels(tables: dict[str, list[dict]], fail) -> None:
    rows = tables["voice-stress/scenarios.csv"]

    # A control named in `expected_control` must carry its violation flag —
    # UNLESS the scenario is a negative control, where the named control is the
    # one under test and the expected outcome is no violation (e.g. the
    # `repeated_disclosure_no_double_count-*` rows: expected_result = ALLOW).
    mismatches = [
        (r["scenario_id"], control)
        for r in rows
        if not truthy(r["is_negative_control"])
        for control, flag in CONTROL_FLAGS.items()
        if control in r["expected_control"] and not truthy(r[flag])
    ]
    if mismatches:
        fail(f"voice-stress/scenarios.csv: {len(mismatches)} non-negative-control "
             f"scenario(s) name a control in expected_control without setting its "
             f"violation flag (e.g. {mismatches[:3]})")

    negatives = [r for r in rows if truthy(r["is_negative_control"])]
    positives = [r for r in rows if not truthy(r["is_negative_control"])]
    unscoreable = [r for r in positives
                   if not any(truthy(r[f]) for f in CORE_FLAGS)]
    got = {
        "negative_controls": len(negatives),
        "positives": len(positives),
        "positives_unscoreable": len(unscoreable),
        "positives_scoreable": len(positives) - len(unscoreable),
    }
    if got != EXPECTED_VOICE_STRESS_POPULATION:
        fail(f"voice-stress/scenarios.csv: scoreable population moved — "
             f"expected {EXPECTED_VOICE_STRESS_POPULATION}, got {got}")

    reasons: dict[str, int] = {}
    for r in unscoreable:
        key = r["expected_control"].strip()
        reasons[key] = reasons.get(key, 0) + 1
    if reasons != EXPECTED_UNSCOREABLE_REASONS:
        fail(f"voice-stress/scenarios.csv: reasons a positive cannot be scored "
             f"moved — expected {EXPECTED_UNSCOREABLE_REASONS}, got {reasons}")


def check_assertion_refs(tables: dict[str, list[dict]], fail) -> None:
    """Every assertion's control_ref is a real control, 'overall', or the
    explicitly-proposed NHID-Auth label."""
    allowed = set(CONTROL_FLAGS) | {
        "overall", "NHID-Auth (proposed, not an existing control)"}
    unknown = {r["control_ref"] for r in tables["voice-stress/assertions.csv"]} - allowed
    if unknown:
        fail(f"voice-stress/assertions.csv: unknown control_ref value(s) "
             f"{sorted(unknown)}")


def check_readme_claims(fail) -> None:
    """The READMEs must state the measured figures verbatim.

    Every number in README_CLAIMS is one this script measures, so a corpus
    change that updates the pinned tables without updating the prose fails
    here.
    """
    for rel, claims in README_CLAIMS.items():
        path = REPO / rel
        if not path.exists():
            fail(f"{rel}: missing — it documents the join key and the stale "
                 f"count columns, and nothing else does")
            continue
        text = path.read_text(encoding="utf-8")
        for claim in claims:
            if claim not in text:
                fail(f"{rel}: does not state {claim!r}")


def main() -> int:
    failures: list[str] = []
    fail = failures.append

    tables = {rel: read(rel) for rel in EXPECTED_ROWS}

    check_row_counts(tables, fail)
    check_unique_keys(tables, fail)

    check_join(tables, "fabricate/conversations.csv", "fabricate/turns.csv",
               "conversation_id", "conversation_ref", fail)
    check_join(tables, "voice-stress/scenarios.csv", "voice-stress/turns.csv",
               "scenario_id", "scenario_id", fail)
    check_join(tables, "voice-stress/scenarios.csv",
               "voice-stress/assertions.csv", "scenario_id", "scenario_id", fail)

    check_declared_counts(tables, "fabricate/conversations.csv",
                          "fabricate/turns.csv", "conversation_id",
                          "num_turns", fail)
    check_declared_counts(tables, "voice-stress/scenarios.csv",
                          "voice-stress/turns.csv", "scenario_id",
                          "num_turns", fail)
    check_declared_counts(tables, "voice-stress/scenarios.csv",
                          "voice-stress/assertions.csv", "scenario_id",
                          "num_assertions", fail)

    check_fabricate_labels(tables, fail)
    check_compliant_population_agrees(tables, fail)
    check_voice_stress_labels(tables, fail)
    check_assertion_refs(tables, fail)
    check_readme_claims(fail)

    if failures:
        for f in failures:
            print("FIXTURE FAIL:", f)
        print(
            "\nIf a fixture change is intentional, update the pinned tables in "
            "scripts/check_fixture_integrity.py and the affected "
            "fixtures/*/README.md in the same commit, and record the new "
            "numbers per docs/MASTER-KNOWLEDGE-ARCHIVE.md §9.1."
        )
        return 1

    print(
        "FIXTURE PASS: fabricate 550 conversations / 4,838 turns; "
        "voice-stress 300 scenarios / 1,582 turns / 2,071 assertions; "
        "join keys resolve to parent 'id'; 3 stale declared-count columns "
        "pinned at their documented divergence; both fixture READMEs state "
        "the measured figures"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
