"""
Fabricate voice-stress corpus — the measurement, pinned
=======================================================
The voice-stress export (fixtures/voice-stress/, 300 scenarios) was staged in
the repository but unrunnable: `convert_voice_stress` existed, but no runner
routed to it. These tests exist so that, now it is wired, three things cannot
drift silently:

  1. the corpus still loads and still has its 95 negative-control (compliant)
     population, so false positives remain measurable;
  2. the measured per-control result stays exactly what was reported in
     docs/validation/FABRICATE_VOICE_STRESS_FINDINGS.md — including the honest
     misses (DBC-01 0/28, EIT-01 12/25). If the engine later detects a case this
     corpus currently misses (good), the test fails and forces the findings doc
     and this pin to move together, so an improvement lands in the open rather
     than silently;
  3. voice-stress and the pinned CSV-550 baseline stay DIFFERENT measurements —
     a regression that routed one corpus through the other's loader would change
     these numbers and trip here.

These are measurements of a synthetic corpus, not a conformance claim.
"""
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SCEN = REPO / "fixtures" / "voice-stress" / "scenarios.csv"
TURNS = REPO / "fixtures" / "voice-stress" / "turns.csv"

pytestmark = pytest.mark.skipif(
    not (SCEN.exists() and TURNS.exists()),
    reason="voice-stress fixtures not present",
)


@pytest.fixture(scope="module")
def conversations():
    from adapters.fabricate_adapter import convert_voice_stress
    return convert_voice_stress(str(SCEN), str(TURNS))


@pytest.fixture(scope="module")
def result(conversations):
    from scripts.confusion_matrix import compute
    return compute(conversations)


def test_corpus_loads_with_its_compliant_population(conversations, result):
    assert len(conversations) == 300
    # The 95 negative controls are the false-positive denominator. If this drops
    # to zero, the is_negative_control -> "compliant" mapping has regressed and
    # FP rates would silently read n/a.
    assert result["n_compliant"] == 95


def _by(result):
    return {c["control"]: c for c in result["controls"]}


@pytest.mark.parametrize("control,detected,expected,fp", [
    ("IDG-01", 65, 65, 0),
    ("PDX-01", 8, 8, 0),
    # The documented gap: DBC-01 detects none of its 28 targeted scenarios.
    # Pinned so a fix cannot land without updating the findings doc with it.
    ("DBC-01", 0, 28, 0),
    ("EIT-01", 12, 25, 6),
])
def test_measured_result_is_what_was_reported(result, control, detected, expected, fp):
    c = _by(result)[control]
    assert (c["detected"], c["expected"], c["fp"]) == (detected, expected, fp), (
        f"{control} moved from the reported voice-stress measurement — update "
        "docs/validation/FABRICATE_VOICE_STRESS_FINDINGS.md and this pin together"
    )


def test_voice_stress_is_not_the_csv550_baseline(result):
    """The two corpora are distinct measurements and must not be conflated. The
    pinned CSV-550 baseline has DBC-01 at 183/200; voice-stress has 0/28. If a
    loader regression routed one through the other, these would collide."""
    from scripts.check_baseline import EXPECTED

    vs = _by(result)
    csv550_dbc = EXPECTED["DBC-01"]          # (183, 200, 5)
    vs_dbc = (vs["DBC-01"]["detected"], vs["DBC-01"]["expected"], vs["DBC-01"]["fp"])
    assert vs_dbc != csv550_dbc
    assert csv550_dbc == (183, 200, 5), "CSV-550 pin changed — not this corpus's job"


def test_the_voice_stress_route_uses_its_own_adapter(monkeypatch):
    """`--voice-stress` must call convert_voice_stress, never convert_csv. A
    typo'd legacy export must not be read as this shape, and vice versa."""
    import scripts.confusion_matrix as cm

    called = {}
    monkeypatch.setattr(cm, "convert_voice_stress",
                        lambda a, b: called.setdefault("vs", (a, b)) or [])
    monkeypatch.setattr(cm, "convert_csv",
                        lambda *a: called.setdefault("csv", a) or [])
    cm.load(["confusion_matrix.py", "--voice-stress", "s.csv", "t.csv"])
    assert called.get("vs") == ("s.csv", "t.csv")
    assert "csv" not in called
