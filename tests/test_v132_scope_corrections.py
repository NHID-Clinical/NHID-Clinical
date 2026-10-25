"""Regression tests for the v1.3.2 scope corrections.

Four changes are locked in here, each of which was made because the previous
behaviour claimed something the framework could not support:

1. The composite score, its trust tiers and its badges are gone. Nothing may
   reintroduce a blended score or a tier vocabulary.
2. DBC-01 ignores caller-supplied artifact flags. The flag was self-reported by
   the agent under evaluation, so it established nothing.
3. The event schema carries transcription attestation, language and
   interpreter-present, so a finding can state the precision it rests on.
4. EIT-01 can distinguish escalation requested / completed / not completed /
   outcome unknown, with unknown as a first-class answer rather than a guess.
"""
import ast
import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.nhid_policy_engine_v1 import (  # noqa: E402
    ESCALATION_COMPLETED,
    ESCALATION_NOT_COMPLETED,
    ESCALATION_NOT_REQUESTED,
    ESCALATION_OUTCOME_UNKNOWN,
    ESCALATION_STATES,
    PolicyAction,
    escalation_state,
    evaluate_dbc01,
)

ROOT = Path(__file__).resolve().parent.parent


def _event(**gov):
    return {
        "event_id": "ev-1",
        "timestamp": "2026-06-01T00:00:00Z",
        "session_id": "s-1",
        "event_type": "POLICY",
        "state_before": "DISCLOSED",
        "healthcare_governance": gov,
        "input_payload": {"speech_text": gov.pop("_speech", "")},
    }


# ── 1. The score, the tiers and the badges stay gone ────────────────────────

#: The traffic-light ladder a withdrawn score is shaped like, whatever it is
#: called. AMBER is here because it is the other common fourth rung.
TIER_COLOURS = frozenset({"GREEN", "YELLOW", "AMBER", "ORANGE", "RED"})

#: Enum bases worth inspecting. `class RiskTier(str, Enum)` carries both.
ENUM_BASES = frozenset({"Enum", "StrEnum", "IntEnum", "IntFlag", "Flag"})


def _tier_shaped(tree: ast.AST) -> list[str]:
    """Every tier-ladder-shaped definition in one parsed module.

    Two shapes, both independent of what anything is named:

      * an Enum whose member NAMES include two or more tier colours, and
      * a function returning two or more tier colours as string literals.

    Deliberately not a scan for the words. `src/pilot_pdf.py` imports AMBER as
    a PDF colour and has every right to; a bare name reference is not a ladder.
    """
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            bases = {b.id for b in node.bases if isinstance(b, ast.Name)}
            bases |= {b.attr for b in node.bases if isinstance(b, ast.Attribute)}
            if not bases & ENUM_BASES:
                continue
            members: set[str] = set()
            for stmt in node.body:
                targets = (
                    [stmt.target] if isinstance(stmt, ast.AnnAssign)
                    else stmt.targets if isinstance(stmt, ast.Assign)
                    else []
                )
                members |= {t.id for t in targets if isinstance(t, ast.Name)}
            if len(members & TIER_COLOURS) >= 2:
                found.append(f"enum {node.name}")
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            returned = {
                sub.value.value.upper()
                for sub in ast.walk(node)
                if isinstance(sub, ast.Return)
                and isinstance(sub.value, ast.Constant)
                and isinstance(sub.value.value, str)
            }
            if len(returned & TIER_COLOURS) >= 2:
                found.append(f"function {node.name}()")
    return found


def test_no_composite_score_survives_under_any_name():
    """The withdrawn score must not come back, whatever it is called.

    This replaces a check that asserted two FILENAMES were absent -- 
    `src/nhid_cas.py` and `src/nhid_badge_generator.py` -- alongside a scan for
    three literal PHRASES ("Verified Trust", "Conditional Trust",
    "badge_eligible"). Both passed while
    `src/safety_evaluation/safety_scorer.py` sat in the package's public API
    computing a composite 0-100 score with GREEN/YELLOW/ORANGE/RED tiers, and
    `adversarial_metrics.assess_robustness_tier` returned the same four colours
    on its own cutoffs. A different filename cleared the first check; four
    colours the phrase list had never heard of cleared the second.

    The guards were keyed on the previous scorer's name and vocabulary rather
    than on what makes a scorer a scorer. This one keys on the shape, so the
    next one cannot evade it by renaming.
    """
    offenders = []
    for path in sorted((ROOT / "src").rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        for shape in _tier_shaped(ast.parse(path.read_text(encoding="utf-8"))):
            offenders.append(f"{path.relative_to(ROOT)}: {shape}")
    assert not offenders, (
        "a risk-tier ladder is back in src/, which README says nothing "
        f"replaces under another name: {offenders}"
    )
    # The two originals, kept so their specific return is still asserted.
    assert not (ROOT / "src" / "nhid_cas.py").exists()
    assert not (ROOT / "src" / "nhid_badge_generator.py").exists()


def test_the_tier_guard_recognises_a_ladder_it_is_meant_to_catch():
    """A guard that has never failed has not been tested.

    Both shapes, written out as the deleted code wrote them.
    """
    as_enum = ast.parse(
        "import enum\n"
        "class RiskTier(str, enum.Enum):\n"
        "    GREEN = 'green'\n"
        "    YELLOW = 'yellow'\n"
        "    RED = 'red'\n"
    )
    assert _tier_shaped(as_enum) == ["enum RiskTier"]

    as_function = ast.parse(
        "def assess(robustness, coverage):\n"
        "    if robustness < 0.5:\n"
        "        return 'RED'\n"
        "    if robustness < 0.85:\n"
        "        return 'YELLOW'\n"
        "    return 'GREEN'\n"
    )
    assert _tier_shaped(as_function) == ["function assess()"]


def test_the_tier_guard_leaves_a_single_colour_and_a_palette_alone():
    """It must not fire on one status word, nor on a colour constant.

    `src/pilot_pdf.py` imports AMBER for PDF styling. A name reference is not
    a ladder, and neither is a lone return value.
    """
    one_colour = ast.parse("def ok():\n    return 'GREEN'\n")
    assert _tier_shaped(one_colour) == []

    palette = ast.parse(
        "from reportlab.lib import colors\n"
        "AMBER = colors.HexColor('#ffbf00')\n"
        "RED = colors.HexColor('#d7263d')\n"
        "def style():\n"
        "    return AMBER\n"
    )
    assert _tier_shaped(palette) == []

    plain_class = ast.parse(
        "class Palette:\n"
        "    GREEN = '#0f0'\n"
        "    RED = '#f00'\n"
    )
    assert _tier_shaped(plain_class) == [], "not an Enum, so not a ladder"


def test_no_trust_tier_vocabulary_in_source():
    """'Verified Trust' / 'Conditional Trust' read as a certification this
    project does not issue. They must not come back anywhere in src/."""
    offenders = []
    for path in (ROOT / "src").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for phrase in ("Verified Trust", "Conditional Trust", "badge_eligible"):
            if phrase in text:
                offenders.append(f"{path.name}: {phrase}")
    assert not offenders, f"withdrawn trust-tier vocabulary reappeared: {offenders}"


def test_handler_reports_evidence_completeness_with_its_denominator():
    """What replaced the score is a fraction that states what it is over."""
    from functions.handler import _evidence_completeness

    result = _evidence_completeness({"event_id": "a", "timestamp": "b"})
    assert result["present"] == 2
    assert result["expected"] == 4
    assert result["fraction"] == 0.5
    assert "tier" not in result and "score" not in result


# ── 2. DBC-01 ignores self-reported artifact flags ──────────────────────────

def test_self_reported_artifact_flag_produces_no_finding():
    decision = evaluate_dbc01({}, _event(deceptive_artifact_flags=["fake_breathing"]))
    assert decision.action == PolicyAction.CONTINUE_AI
    assert decision.violations == []


def test_persona_claim_is_still_caught_from_what_was_said():
    decision = evaluate_dbc01(
        {}, _event(identity_assertion_text="I'm one of the nurses on our team.")
    )
    assert decision.action == PolicyAction.LOG_ONLY
    assert any(v.rule_id == "DBC-01" for v in decision.violations)


def test_artifact_flag_cannot_escalate_a_persona_finding_to_critical():
    """Even alongside a real persona match, the flag must add nothing."""
    decision = evaluate_dbc01(
        {},
        _event(
            identity_assertion_text="I'm one of the nurses on our team.",
            deceptive_artifact_flags=["fake_breathing", "fake_typing"],
        ),
    )
    assert all(v.severity.value != "critical" for v in decision.violations)
    assert decision.reason_code == "DBC01_IMPERSONATION_PHRASE_DETECTED"


# ── 3. The schema carries what a finding rests on ───────────────────────────

@pytest.fixture(scope="module")
def schema():
    return json.loads((ROOT / "schema" / "nhid_trace_schema_v1.json").read_text())


def test_schema_carries_transcription_attestation(schema):
    gov = schema["properties"]["healthcare_governance"]["properties"]
    att = gov["transcription_attestation"]
    assert set(att["properties"]["status"]["enum"]) == {"measured", "attested", "unattested"}
    assert att["required"] == ["status"]


def test_schema_carries_language_and_interpreter(schema):
    gov = schema["properties"]["healthcare_governance"]["properties"]
    assert "language" in gov
    assert "interpreter_present" in gov


def test_artifact_field_is_documented_as_ignored(schema):
    gov = schema["properties"]["healthcare_governance"]["properties"]
    desc = gov["deceptive_artifact_flags"]["description"]
    assert "IGNORED" in desc and "self-reported" in desc


# ── 4. EIT-01 distinguishes four outcomes, and admits when it cannot ────────

def test_no_request_is_not_requested():
    assert escalation_state({}, _event()) == ESCALATION_NOT_REQUESTED


def test_request_with_completion_is_completed():
    state = escalation_state(
        {}, _event(escalation_timestamp="2026-06-01T00:01:00Z", escalation_outcome="transferred")
    )
    assert state == ESCALATION_COMPLETED


def test_request_that_was_deflected_is_not_completed():
    state = escalation_state(
        {}, _event(escalation_timestamp="2026-06-01T00:01:00Z", escalation_outcome="deflected")
    )
    assert state == ESCALATION_NOT_COMPLETED


def test_request_with_no_reported_outcome_is_unknown_not_completed():
    """The governance failure this exists to expose: a request that was made and
    whose completion nobody recorded. Guessing either way invents a fact."""
    state = escalation_state({}, _event(escalation_timestamp="2026-06-01T00:01:00Z"))
    assert state == ESCALATION_OUTCOME_UNKNOWN


def test_unrecognised_outcome_is_unknown_not_completed():
    state = escalation_state(
        {}, _event(escalation_timestamp="2026-06-01T00:01:00Z", escalation_outcome="¯\\_(ツ)_/¯")
    )
    assert state == ESCALATION_OUTCOME_UNKNOWN


def test_escalation_state_never_raises():
    for bad in (None, {}, {"healthcare_governance": "not-a-dict"}):
        assert escalation_state({}, bad or {}) in ESCALATION_STATES
