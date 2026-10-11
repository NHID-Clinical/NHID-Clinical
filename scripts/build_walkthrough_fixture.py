#!/usr/bin/env python3
"""
Generate the Front-Desk Walkthrough's playback fixture from the real engine.

The walkthrough at assets/media/front-desk-walkthrough.html used to hold four
hand-written step arrays with literal "IDG-01 PASS" / "PDX-01 FAIL" strings in
them. Nothing computed those verdicts; a reader had no way to tell the picture
apart from an illustration, and the caption on developers.html said as much.

This script removes that gap the same way scripts/build_gateway_fixture.py did
for the Trust Gateway: replay real corpus scenarios through the real engine and
record what it returned. The browser then *plays back* a recording. It never
decides anything.

    real engine behaviour -> generated trace -> visual playback

Every action, reason code, violation and control verdict in the output is
`evaluate_all` / `evaluate_*` output. Every scenario input is copied from
tests/evaluation_corpus_v1.json without modification. Every reason code listed
in the rule_engine.config panels is scraped out of the engine source, so a code
that does not exist in the engine cannot appear on the page.

The one thing this script decides on its own is *stage order*: the character
walks IDG-01 -> PDX-01 -> DBC-01 -> EIT-01, left to right, always. That is a
choreography decision, deliberately independent of the engine's evaluation and
priority order, and it is documented as such in STAGE_ORDER below.

Usage:
    python scripts/build_walkthrough_fixture.py            # write the fixture
    python scripts/build_walkthrough_fixture.py --check    # verify, write nothing
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.nhid_policy_engine_v1 import (  # noqa: E402
    evaluate_all,
    evaluate_atr01,
    evaluate_dbc01,
    evaluate_eit01,
    evaluate_idg01,
    evaluate_pdx01,
)
from src.synthetic_eval_loop import (  # noqa: E402
    build_event,
    build_session,
    carry_disclosure_forward,
)

CORPUS = ROOT / "tests" / "evaluation_corpus_v1.json"
ENGINE = ROOT / "src" / "nhid_policy_engine_v1.py"
OUT = ROOT / "assets" / "data" / "walkthrough-trace.json"
PAGE = ROOT / "assets" / "media" / "front-desk-walkthrough.html"

# The trace is inlined into the page rather than fetched at runtime. The frame
# is sandboxed without allow-same-origin, so its origin is opaque and a fetch
# back to the site would be a null-origin cross-origin request. Inlining also
# keeps the fixture and the markup that renders it under one drift guard —
# the same arrangement scripts/build_gateway_fixture.py uses.
BEGIN = "<!-- BEGIN GENERATED walkthrough-trace -->"
END = "<!-- END GENERATED walkthrough-trace -->"

GROUPS = ("compliant_scenarios", "single_rule_violations", "multi_rule_combinations")

# The five scenarios the walkthrough offers. Each is a real corpus scenario;
# the label is what the scenario demonstrates, not a claim about its outcome —
# the outcome is whatever the engine returns below.
SCENARIOS: tuple[tuple[str, str, str], ...] = (
    ("nhid_ec_comp_001", "Conformant pass", "Disclosure first, then data"),
    ("nhid_ec_idg01_001", "IDG-01 failure", "No identity disclosure"),
    ("nhid_ec_pdx01_001", "PDX-01 failure", "Protected data before disclosure"),
    ("nhid_ec_dbc01_001", "DBC-01 failure", "False human-role claim"),
    ("nhid_ec_comp_002", "EIT-01 escalation", "Human handoff honored"),
)

# ── Reading order, not engine order ─────────────────────────────────────────
# The engine evaluates every control on every turn and resolves them by
# priority (DENY_DATA 5 > ESCALATE_HUMAN 4 > DISCLOSE_IDENTITY 3 > LOG_ONLY 2 >
# CONTINUE_AI 1). This tuple is neither of those things: it is the order the
# four behavioural controls are *listed* in, top to bottom, so a reader meets
# them in the order the specification introduces them.
#
# An earlier version of the page staged these four as a corridor of arches and
# walked a figure through them left to right. That read as a pipeline, which is
# the one thing the control set is not — all five are evaluated on every turn,
# and none of them waits for the one before it. The readout now shows five rows
# every turn precisely so that cannot be misread.
#
# ATR-01 is deliberately absent from this tuple. It gates nothing: it is the
# evidence layer every turn is written into whatever the other four returned,
# and the page draws it apart from them for that reason. The page derives its
# own display order from this tuple plus whatever `is_station` marks as not a
# gate, so ATR-01 cannot be promoted into the gate list by editing the page.
STAGE_ORDER: tuple[str, ...] = ("IDG-01", "PDX-01", "DBC-01", "EIT-01")

CONTROL_NAMES = {
    "IDG-01": "Identity Disclosure Gate",
    "PDX-01": "Pre-Data Exchange Gate",
    "DBC-01": "Deceptive Behavior Check",
    "EIT-01": "Escalation Implementation Test",
    "ATR-01": "Audit Trail",
}

# What each control is for, in one line, for the config panel. These describe
# the control's job — not where it sits, because it no longer sits anywhere.
# They make no claim about what the engine returned on any given turn.
#
# The previous set described furniture ("Reception arch", "Records window",
# "Voice bench", "Handoff desk"). That was staging language for a room that no
# longer exists, and while the room stood it was also doing the explaining.
CONTROL_STAGING = {
    "IDG-01": "Has the agent disclosed that it is not human, and does its own "
              "identity assertion still say so?",
    "PDX-01": "Is protected health information being exchanged, and was "
              "disclosure on record before it was?",
    "DBC-01": "Does the agent's speech claim human or licensed-professional "
              "status? Text only — this control does not analyse audio.",
    "EIT-01": "Was a human handoff asked for, and did one actually happen?",
    "ATR-01": "Is the turn's audit envelope complete? Written on every turn, "
              "pass or fail; it gates nothing.",
}

# The engine's own priority ladder, read from the source rather than retyped.
PRIORITY_PATTERN = re.compile(
    r"PolicyAction\.(?P<action>[A-Z_]+)\s*:\s*(?P<priority>\d+)"
)
REASON_CODE_PATTERN = "{prefix}_[A-Z_]+"


def _load_scenarios() -> dict[str, dict[str, Any]]:
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    found: dict[str, dict[str, Any]] = {}
    wanted = {sid for sid, _, _ in SCENARIOS}
    for group in GROUPS:
        for scenario in corpus.get(group, []):
            if scenario["scenario_id"] in wanted:
                found[scenario["scenario_id"]] = scenario
    missing = wanted - set(found)
    if missing:
        raise SystemExit(
            f"WALKTHROUGH FAIL: {sorted(missing)} not present in "
            f"{CORPUS.relative_to(ROOT)}."
        )
    return found


def _action_priority() -> dict[str, int]:
    """Read the enforcement ladder out of the engine instead of retyping it."""
    source = ENGINE.read_text(encoding="utf-8")
    ladder = {m.group("action"): int(m.group("priority"))
              for m in PRIORITY_PATTERN.finditer(source)}
    if not ladder:
        raise SystemExit(
            "WALKTHROUGH FAIL: could not read the priority ladder out of "
            f"{ENGINE.relative_to(ROOT)}. The engine's `_priority` mapping moved; "
            "update PRIORITY_PATTERN rather than hard-coding the numbers."
        )
    return ladder


def _reason_codes(control_id: str) -> list[str]:
    """Scrape a control's reason codes from the engine source.

    A code that is not in the engine cannot reach the config panel, which is
    what stops the panels drifting into fiction.
    """
    prefix = control_id.replace("-", "")
    source = ENGINE.read_text(encoding="utf-8")
    codes = sorted(set(re.findall(REASON_CODE_PATTERN.format(prefix=prefix), source)))
    if not codes:
        raise SystemExit(
            f"WALKTHROUGH FAIL: no reason codes found for {control_id} in "
            f"{ENGINE.relative_to(ROOT)}."
        )
    return codes


def _commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT, capture_output=True, text=True, check=True,
        ).stdout.strip()
    except Exception:
        return "unknown"


def _decision(decision: Any) -> dict[str, Any]:
    return {
        "action": decision.action.name,
        "reason_code": decision.reason_code,
        "violations": [
            {
                "rule_id": v.rule_id,
                "severity": v.severity.name,
                "description": v.description,
            }
            for v in decision.violations
        ],
    }


def _controls(session: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    """Per-control decisions, so each station's lamp is that control's own verdict.

    `evaluate_all` returns one composite decision; a scene with four stations
    needs to know which control produced what. These are the same functions
    `evaluate_all` calls, on the same session and event.
    """
    return {
        "IDG-01": _decision(evaluate_idg01(session, event)),
        "PDX-01": _decision(evaluate_pdx01(session, event)),
        "DBC-01": _decision(evaluate_dbc01(session, event)),
        "EIT-01": _decision(evaluate_eit01(session, event)),
        "ATR-01": _decision(evaluate_atr01(session, event)),
    }


def build() -> dict[str, Any]:
    """Replay each scenario through the engine and record what it returned."""
    scenarios = _load_scenarios()
    ladder = _action_priority()

    out: dict[str, Any] = {
        "generated_by": "scripts/build_walkthrough_fixture.py",
        "source_corpus": "tests/evaluation_corpus_v1.json",
        "engine": "src/nhid_policy_engine_v1.py :: evaluate_all",
        "note": (
            "Every action, reason code, violation and per-control verdict below "
            "is the engine's own output, recorded by replaying real corpus "
            "scenarios. Scenario inputs are copied from the corpus unchanged. "
            "Nothing here is written by hand."
        ),
        "choreography_note": (
            "stage_order is a visual decision, not an engine one. The engine "
            "evaluates all five controls on every turn and resolves them by "
            "priority; the scene walks the agent through four stations left to "
            "right so the room reads as a room. ATR-01 is not a station — it is "
            "the evidence ledger."
        ),
        "action_priority": ladder,
        "stage_order": list(STAGE_ORDER),
        "controls": {
            control_id: {
                "control_id": control_id,
                "name": CONTROL_NAMES[control_id],
                "staging": CONTROL_STAGING[control_id],
                "is_station": control_id in STAGE_ORDER,
                "reason_codes": _reason_codes(control_id),
            }
            for control_id in CONTROL_NAMES
        },
        "scenarios": [],
    }

    for scenario_id, label, sublabel in SCENARIOS:
        scenario = scenarios[scenario_id]
        turns = []
        for index, turn in enumerate(carry_disclosure_forward(scenario["turns"])):
            session = build_session(turn)
            event = build_event(scenario_id, index, turn)
            composite = evaluate_all(session, event)
            turns.append({
                "index": index,
                "speech": (turn.get("speech_text") or "").strip(),
                "assertion": (turn.get("identity_assertion_text") or "").strip(),
                "phi_accessed": list(turn.get("phi_accessed") or []),
                "deceptive_artifact_flags": list(turn.get("deceptive_artifact_flags") or []),
                "escalation_path_available": bool(turn.get("escalation_path_available", True)),
                "composite": _decision(composite),
                "controls": _controls(session, event),
            })
        out["scenarios"].append({
            "id": scenario_id,
            "label": label,
            "sublabel": sublabel,
            "title": scenario.get("title", scenario_id),
            "description": scenario.get("description", ""),
            "expected_violations": scenario.get("expected_violations") or [],
            "turns": turns,
        })
    return out


def render_block(data: dict[str, Any]) -> str:
    """The generated <script type="application/json"> block, exactly as injected."""
    # `</script>` inside JSON would close the tag early; the forward slash is
    # escaped so the payload can never break out of the element.
    payload = json.dumps(data, indent=2, sort_keys=False).replace("</", "<\\/")
    return (
        f"{BEGIN}\n"
        f'<script type="application/json" id="walkthroughTrace">\n'
        f"{payload}\n"
        f"</script>\n"
        f"{END}"
    )


def inject(data: dict[str, Any]) -> bool:
    """Write the generated block into the page. Returns True if it changed."""
    page = PAGE.read_text(encoding="utf-8")
    if BEGIN not in page or END not in page:
        raise SystemExit(
            f"WALKTHROUGH FAIL: {PAGE.name} has lost its generated block markers."
        )
    start = page.index(BEGIN)
    stop = page.index(END) + len(END)
    block = render_block(data)
    if page[start:stop] == block:
        return False
    PAGE.write_text(page[:start] + block + page[stop:], encoding="utf-8")
    return True


def _strip_comments(src: str) -> str:
    """Remove HTML, CSS/JS block and JS line comments.

    The invariants below grep the page for engine output that has been typed in
    by hand. Comments must not count: this file's own rules are explained in
    comments *inside* that page, and a check that fires on the explanation is a
    check that gets the explanation deleted. Nothing in a comment reaches a
    reader's screen, so nothing in a comment can mislead one.
    """
    src = re.sub(r"<!--.*?-->", " ", src, flags=re.S)      # HTML
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)       # CSS and JS block
    src = re.sub(r"(?m)^\s*//.*$", " ", src)               # JS line, own line
    return src


def _authored_invariants(data: dict[str, Any]) -> list[str]:
    """Properties of the scene that the engine cannot state for itself.

    These live here rather than in tests/ deliberately. The repository enforces
    atomic propagation of the published unit-test count across every surface
    that prints it (scripts/check_number_drift.py), so adding pytest cases to
    assert them would force an unrelated count-propagation commit across the
    README, the homepage and the PDF generator. They run in CI as part of
    --check instead, which is the same protection at the same cadence.
    """
    problems: list[str] = []
    page = PAGE.read_text(encoding="utf-8")

    # 1. ATR-01 is the evidence ledger, not a booth anyone walks into.
    if "ATR-01" in STAGE_ORDER:
        problems.append("ATR-01 has been added to STAGE_ORDER; it is the ledger, not a stop.")
    if data["controls"]["ATR-01"]["is_station"]:
        problems.append("ATR-01 is marked as a station.")

    # 2. The readout must build itself from this trace, not from a list typed
    #    into the page.
    #
    #    This replaces an invariant that asserted a set of floor coordinates
    #    (STATION_X) ascended left to right, which kept the walking figure from
    #    appearing to reverse. There is no floor any more, so that check had
    #    nothing left to protect. What needs protecting now is the property the
    #    redesign rests on: the page derives its five rows and its composite
    #    line from the fixture, so a control cannot appear on the glass that
    #    the engine did not evaluate, and ATR-01 cannot be promoted into the
    #    gate list by editing markup.
    #    Searched in the AUTHORED region only. Searching the whole page passes
    #    vacuously: the generated block below is JSON that contains every one of
    #    these keys, so the check could never fail however the script was
    #    rewritten. Caught by replacing the lookup with a hardcoded map and
    #    watching this check pass anyway.
    authored_for_keys = _strip_comments(
        page[page.index("<body"):page.index(BEGIN)] + page[page.index(END):]
    )
    for needle, why in (
        ("TRACE.stage_order", "derive the behavioural rows from the trace"),
        ("is_station", "tell a gate from the evidence layer"),
        ("TRACE.action_priority", "resolve the composite action"),
    ):
        if needle not in authored_for_keys:
            problems.append(
                f"the readout no longer reads `{needle}`; it must, to {why}."
            )

    # 3. No verdict may be typed into the page by hand. This is the exact defect
    #    the first rebuild removed, and a redesign is the likeliest moment to
    #    reintroduce it — drawing the readout into the artwork would look fine
    #    and be just as wrong.
    #
    #    Comments are stripped before any of this runs. A guard that fires on
    #    prose describing the rule teaches the next person to delete the prose,
    #    and a verdict inside a comment renders to nobody, so it cannot mislead
    #    a reader. The same reasoning is written up in scripts/check_offline_kit.py.
    start = page.index(BEGIN)
    stop = page.index(END)
    authored = _strip_comments(page[:start] + page[stop:])

    hand_written = re.findall(
        r"(?:IDG|PDX|DBC|EIT|ATR)-01\s+(?:PASS|FAIL|PASSED|FAILED)", authored, re.I
    )
    if hand_written:
        problems.append(f"hand-written verdicts found in the scene: {hand_written}")

    #    The markup region is held to a stricter rule than the script. The
    #    script legitimately names every action once, to map it to a colour;
    #    the markup has no business naming one at all, because every cell that
    #    shows an action or a reason code is written at runtime. An action name
    #    or reason code appearing here means someone has drawn the output.
    body_start = page.index("<body")
    markup = _strip_comments(page[body_start:start])
    drawn = sorted(set(
        re.findall(r"\b(?:CONTINUE_AI|DENY_DATA|ESCALATE_HUMAN|DISCLOSE_IDENTITY|LOG_ONLY)\b", markup)
        + re.findall(r"\b(?:IDG|PDX|DBC|EIT|ATR)01_[A-Z_]+\b", markup)
    ))
    if drawn:
        problems.append(
            f"engine output is drawn into the markup: {drawn}. Every action and "
            f"reason code on the screen must be written at runtime from the trace."
        )

    # 4. Every reason code the config panels advertise must exist in the engine.
    engine = ENGINE.read_text(encoding="utf-8")
    for control_id, meta in data["controls"].items():
        for code in meta["reason_codes"]:
            if not re.search(rf"\b{re.escape(code)}\b", engine):
                problems.append(f"{control_id} advertises {code}, absent from the engine.")

    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="fail if the committed fixture is missing or stale")
    args = ap.parse_args(argv)

    fresh = build()

    if args.check:
        if not OUT.exists():
            print(f"WALKTHROUGH FAIL: {OUT.relative_to(ROOT)} does not exist. "
                  "Run scripts/build_walkthrough_fixture.py.", file=sys.stderr)
            return 1
        committed = json.loads(OUT.read_text(encoding="utf-8"))
        # source_commit churns on every commit; compare only what the page reads.
        for key in ("scenarios", "controls", "action_priority", "stage_order"):
            if committed.get(key) != fresh[key]:
                print(f"WALKTHROUGH FAIL: {OUT.relative_to(ROOT)} no longer matches "
                      f"what the engine produces (`{key}` differs). Re-run "
                      "scripts/build_walkthrough_fixture.py and commit the result.",
                      file=sys.stderr)
                return 1

        page = PAGE.read_text(encoding="utf-8")
        if BEGIN not in page or END not in page:
            print(f"WALKTHROUGH FAIL: {PAGE.name} has lost its generated block.",
                  file=sys.stderr)
            return 1
        rendered = page[page.index(BEGIN):page.index(END) + len(END)]
        # The page carries source_commit too, so compare against the committed
        # fixture's copy of it rather than re-deriving one that would churn.
        expected = dict(fresh)
        if "source_commit" in committed:
            expected["source_commit"] = committed["source_commit"]
        if rendered != render_block(expected):
            print("WALKTHROUGH FAIL: the trace embedded in "
                  "assets/media/front-desk-walkthrough.html no longer matches the "
                  "engine's output. Re-run scripts/build_walkthrough_fixture.py "
                  "and commit the result.", file=sys.stderr)
            return 1

        problems = _authored_invariants(fresh)
        if problems:
            for problem in problems:
                print(f"WALKTHROUGH FAIL: {problem}", file=sys.stderr)
            return 1

        turns = sum(len(s["turns"]) for s in fresh["scenarios"])
        print(f"WALKTHROUGH PASS: fixture and readout match the engine "
              f"({len(fresh['scenarios'])} scenarios, {turns} turns); "
              f"five controls render from the trace and ATR-01 is not a gate")
        return 0

    fresh["source_commit"] = _commit()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(fresh, indent=2) + "\n", encoding="utf-8")
    changed = inject(fresh)
    turns = sum(len(s["turns"]) for s in fresh["scenarios"])
    print(f"Wrote {OUT.relative_to(ROOT)} — {len(fresh['scenarios'])} scenarios, "
          f"{turns} turns")
    print(f"{PAGE.name}: generated block " + ("updated" if changed else "already current"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
