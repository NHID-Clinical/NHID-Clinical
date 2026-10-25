#!/usr/bin/env python3
"""
Trust Gateway fixture — real engine output, not an illustration
===============================================================
The walkthrough this replaces was labelled, honestly, "Illustrative — dialogue,
mock config payloads, and artwork are for explanation only." That is the right
disclaimer for a mock, and the wrong artifact for a page whose whole argument is
that the controls are checkable.

So this script does not write an example. It runs `evaluate_all` — the same
function the conformance suite and the hosted API call — over real scenarios
from the governance evaluation corpus, and records exactly what came back: the
action, the reason code, and every violation, verbatim.

Two scenarios are included, chosen for what they teach rather than for how they
score:

  nhid_ec_comp_001   a compliant call. Disclosure first, then the data request.
  nhid_ec_combo_008  the failure this project exists for. A human persona, PHI
                     requested with no disclosure at all, and an escalation
                     that is not honoured.

The output is committed so the page needs no network and no server. A test
regenerates it and fails if the committed copy has drifted, which is what keeps
"real engine output" true rather than merely claimed.

Usage:
    python scripts/build_gateway_fixture.py            # write the fixture
    python scripts/build_gateway_fixture.py --check    # verify, write nothing
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from src.nhid_policy_engine_v1 import (  # noqa: E402
    evaluate_all,
    evaluate_atr01,
    evaluate_dbc01,
    evaluate_eit01,
    evaluate_idg01,
    evaluate_pdx01,
)
from synthetic_eval_loop import (  # noqa: E402
    build_event,
    build_session,
    carry_disclosure_forward,
)

CORPUS = ROOT / "tests" / "evaluation_corpus_v1.json"
OUT = ROOT / "assets" / "data" / "gateway-trace.json"
PAGE = ROOT / "specification.html"

#: Headings shown on the page for two corpus scenarios. The corpus titles are
#: internal labels ("Quadruple: ...", "Fully Compliant: ...") and the corpus is
#: pinned data, so the rename lives here rather than in the fixture: the
#: scenario ids, turns and engine output are untouched.
DISPLAY_TITLES = {
    "nhid_ec_comp_001": "Scenario A: disclosed call, no violations",
    "nhid_ec_combo_008": "Scenario B: four controls fire",
}
BEGIN = "<!-- BEGIN GENERATED trust-gateway -->"
END = "<!-- END GENERATED trust-gateway -->"

# Chosen for what they demonstrate. Both are real corpus scenarios, replayed
# through the real engine; neither was written for this page.
SCENARIOS = ("nhid_ec_comp_001", "nhid_ec_combo_008")

SPEAKER_NOTE = {
    "nhid_ec_comp_001": "A compliant call. The agent discloses, waits, and only then asks.",
    "nhid_ec_combo_008": "The failure mode this project exists for: a human persona, "
                         "protected data requested with no disclosure, and an escalation "
                         "request that goes unhonoured.",
}

# ── The home-page hero transcript ────────────────────────────────────────────
# The brief asked for the hero to replay nhid_ec_comp_001. Its first turn is
# "Thank you for calling... your member information": the agent ANSWERING a
# member's call, the reversed direction CLAUDE.md §1 forbids on any published
# surface. So the hero uses a three-turn caller-side script written here, and
# keeps the part that matters true: every chip is the engine's own output for
# exactly these words, from the same evaluators the suite and the API call.
# The representative's turn is display only; the controls judge the agent.
HOME = ROOT / "index.html"
HERO_BEGIN = "<!-- BEGIN GENERATED hero-transcript -->"
HERO_END = "<!-- END GENERATED hero-transcript -->"
HERO_ID = "hero_disclosed_call"
HERO_LABEL = "A conceptual model, not a recorded call."
HERO_TURNS = (
    {"speaker": "agent",
     "speech_text": "Hi, this is an automated AI assistant calling on behalf of Dr. Patel's "
                    "office about the status of a claim.",
     "identity_assertion_text": "automated AI assistant",
     "disclosure_timestamp": "2026-06-01T00:00:00Z",
     "turn_count": 0, "phi_accessed": []},
    {"speaker": "representative",
     "speech_text": "Thanks for letting me know. What do you need today?"},
    {"speaker": "agent",
     "speech_text": "Can you confirm the member ID on claim 48213 so I can check its status?",
     "turn_count": 2, "phi_accessed": ["member_id"]},
)
#: Reason codes that mean "this control had nothing to judge on this turn".
#: They render as a muted "no finding" chip; the code itself stays in the markup.
QUIET_CODES = {
    "PDX01_NO_PHI_REQUESTED",
    "DBC01_NO_ARTIFACTS",
    "EIT01_NO_ESCALATION_REQUESTED",
}
PER_CONTROL = (
    ("IDG-01", evaluate_idg01),
    ("PDX-01", evaluate_pdx01),
    ("DBC-01", evaluate_dbc01),
    ("EIT-01", evaluate_eit01),
)


def _load_scenarios() -> dict:
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    found = {}
    for group in ("compliant_scenarios", "single_rule_violations", "multi_rule_combinations"):
        for scenario in corpus.get(group, []):
            if scenario["scenario_id"] in SCENARIOS:
                found[scenario["scenario_id"]] = scenario
    missing = set(SCENARIOS) - set(found)
    if missing:
        raise SystemExit(f"scenario(s) not in the corpus: {sorted(missing)}")
    return found


def _commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT, capture_output=True, text=True, check=True,
        ).stdout.strip()
    except Exception:
        return "unknown"


def build_hero() -> dict:
    """Run the hero script's agent turns through the engine, one control at a time.

    Disclosure is carried forward exactly as the corpus replay does it, so the
    second agent turn is judged as "disclosed before this turn" and PDX-01 can
    report the gate as cleared rather than tripped.
    """
    agent_turns = [dict(t) for t in HERO_TURNS if t["speaker"] == "agent"]
    carried = iter(carry_disclosure_forward(agent_turns))
    turns = []
    for position, spoken in enumerate(HERO_TURNS):
        if spoken["speaker"] != "agent":
            turns.append({"position": position, "speaker": "representative",
                          "speech": spoken["speech_text"], "evaluated": False})
            continue
        turn = next(carried)
        session, event = build_session(turn), build_event(HERO_ID, position, turn)
        composite = evaluate_all(session, event)
        controls = []
        for rule_id, evaluator in PER_CONTROL:
            d = evaluator(session, event)
            controls.append({"rule_id": rule_id, "action": d.action.name,
                             "reason_code": d.reason_code,
                             "quiet": d.reason_code in QUIET_CODES})
        atr = evaluate_atr01(session, event)
        turns.append({
            "position": position, "speaker": "agent", "speech": spoken["speech_text"],
            "evaluated": True, "controls": controls,
            "audit": {"rule_id": "ATR-01", "action": atr.action.name, "reason_code": atr.reason_code},
            "composite": {"action": composite.action.name, "reason_code": composite.reason_code},
        })
    return {"id": HERO_ID, "label": HERO_LABEL, "turns": turns}


def build() -> dict:
    """Replay each scenario through the engine and record what it returned."""
    scenarios = _load_scenarios()
    out = {
        "generated_by": "scripts/build_gateway_fixture.py",
        "source_corpus": "tests/evaluation_corpus_v1.json",
        "engine": "src/nhid_policy_engine_v1.py :: evaluate_all",
        "note": (
            "Every action, reason code and violation below is the engine's own "
            "output, recorded by replaying real corpus scenarios. Nothing here "
            "is written by hand."
        ),
        "scenarios": [],
    }

    for scenario_id in SCENARIOS:
        scenario = scenarios[scenario_id]
        turns = []
        for index, turn in enumerate(carry_disclosure_forward(scenario["turns"])):
            decision = evaluate_all(build_session(turn), build_event(scenario_id, index, turn))
            turns.append({
                "index": index,
                "speech": (turn.get("speech_text") or "").strip(),
                "assertion": (turn.get("identity_assertion_text") or "").strip(),
                "disclosed_before_this_turn": bool(turn.get("disclosure_timestamp"))
                and turn.get("disclosure_established_prior", False),
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
            })
        out["scenarios"].append({
            "id": scenario_id,
            "title": DISPLAY_TITLES.get(scenario_id, scenario.get("title", scenario_id)),
            "expected_violations": scenario.get("expected_violations") or [],
            "note": SPEAKER_NOTE[scenario_id],
            "turns": turns,
        })
    out["hero_transcript"] = build_hero()
    return out


ACTION_TONE = {
    "DENY_DATA": "deny",
    "ESCALATE_HUMAN": "escalate",
    "DISCLOSE_IDENTITY": "disclose",
    "LOG_ONLY": "log",
    "CONTINUE_AI": "continue",
}


def _esc(text: str) -> str:
    return (text.replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;").replace('"', "&quot;"))


def render_html(data: dict) -> str:
    """Render every turn into static HTML.

    Server-rendered on purpose: the whole point of this component is that the
    output is real, so it has to be readable with JavaScript disabled. The
    script in site.js only adds stepping on top of content that is already
    there and already complete.
    """
    out = [BEGIN]
    for scenario in data["scenarios"]:
        out.append(f'        <section class="tg-scenario" data-scenario="{_esc(scenario["id"])}">')
        out.append(f'          <h3 class="tg-scenario-title">{_esc(scenario["title"])}</h3>')
        out.append(f'          <p class="tg-scenario-note">{_esc(scenario["note"])}</p>')
        out.append('          <ol class="tg-turns">')
        for turn in scenario["turns"]:
            tone = ACTION_TONE.get(turn["action"], "log")
            out.append(f'            <li class="tg-turn" data-turn="{turn["index"]}">')
            out.append('              <div class="tg-said">')
            out.append(f'                <span class="tg-turn-no">Turn {turn["index"]}</span>')
            out.append(f'                <q>{_esc(turn["speech"])}</q>')
            out.append("              </div>")
            out.append('              <div class="tg-verdict">')
            out.append(f'                <span class="tg-action tg-action-{tone}">{_esc(turn["action"])}</span>')
            out.append(f'                <code class="tg-reason">{_esc(turn["reason_code"])}</code>')
            out.append("              </div>")
            if turn["violations"]:
                out.append('              <ul class="tg-violations">')
                for v in turn["violations"]:
                    out.append(
                        f'                <li><b>{_esc(v["rule_id"])}</b> '
                        f'<span class="tg-sev">{_esc(v["severity"])}</span> '
                        f'{_esc(v["description"])}</li>'
                    )
                out.append("              </ul>")
            else:
                out.append('              <p class="tg-clean">No violation on this turn.</p>')
            out.append("            </li>")
        out.append("          </ol>")
        out.append("        </section>")
    out.append(f"        {END}")
    return "\n".join(out)


def inject(data: dict) -> bool:
    """Replace the generated block in specification.html. Returns True if changed."""
    page = PAGE.read_text(encoding="utf-8")
    if BEGIN not in page or END not in page:
        raise SystemExit(
            f"{PAGE.name} has no generated block; add {BEGIN} / {END} markers first"
        )
    start = page.index(BEGIN)
    finish = page.index(END) + len(END)
    fresh = render_html(data)
    if page[start:finish] == fresh:
        return False
    PAGE.write_text(page[:start] + fresh + page[finish:], encoding="utf-8")
    return True


def render_hero(hero: dict) -> str:
    """The home-page transcript: three turns, chips per control, ATR-01 band.

    Server-rendered like the Trust Gateway. The label says what it is; the
    caption says what the chips do not mean.
    """
    out = [HERO_BEGIN,
           '          <figure class="hero-transcript" aria-labelledby="ht-label">',
           '            <figcaption class="ht-label" id="ht-label">'
           f'<span class="maturity-reference">Reference</span> {_esc(hero["label"])} '
           'Every chip is the reference engine&rsquo;s own output for the words shown.</figcaption>',
           '            <ol class="ht-turns">']
    audit_codes: list[str] = []
    for turn in hero["turns"]:
        if not turn["evaluated"]:
            out.append(f'              <li class="ht-turn ht-rep" data-turn="{turn["position"]}">')
            out.append('                <span class="ht-who">Payer representative</span>')
            out.append(f'                <q>{_esc(turn["speech"])}</q>')
            out.append('                <span class="ht-note">Not evaluated: the controls judge the agent&rsquo;s turns.</span>')
            out.append('              </li>')
            continue
        out.append(f'              <li class="ht-turn ht-agent" data-turn="{turn["position"]}">')
        out.append('                <span class="ht-who">AI agent &middot; calling for a provider</span>')
        out.append(f'                <q>{_esc(turn["speech"])}</q>')
        out.append('                <ul class="ht-chips" aria-label="What each control returned for this turn">')
        for c in turn["controls"]:
            state = "is-quiet" if c["quiet"] else "is-lit"
            shown = "no finding" if c["quiet"] else c["reason_code"]
            out.append(f'                  <li class="ht-chip {state}" data-control="{c["rule_id"]}" '
                       f'data-reason="{_esc(c["reason_code"])}"><b>{c["rule_id"]}</b>'
                       f'<code>{_esc(shown)}</code></li>')
        out.append(f'                  <li class="ht-composite"><span>composite</span>'
                   f'<code>{_esc(turn["composite"]["action"])}</code></li>')
        out.append('                </ul>')
        out.append('              </li>')
        if turn["audit"]["reason_code"] not in audit_codes:
            audit_codes.append(turn["audit"]["reason_code"])
    out.append('            </ol>')
    out.append('            <p class="ht-audit"><b>ATR-01</b><span>Records every turn. Changes no behavior.</span>'
               f'<code>{_esc(" · ".join(audit_codes))}</code></p>')
    out.append('            <p class="ht-caption">Disclosure is not authorization: the chips show what the agent '
               'said and when, not that it may receive the data.</p>')
    out.append('          </figure>')
    out.append(f'          {HERO_END}')
    return "\n".join(out)


def inject_hero(data: dict) -> bool:
    """Replace the generated hero block in index.html. Returns True if changed."""
    page = HOME.read_text(encoding="utf-8")
    if HERO_BEGIN not in page or HERO_END not in page:
        raise SystemExit(f"{HOME.name} has no generated hero block; add {HERO_BEGIN} / {HERO_END} markers first")
    start = page.index(HERO_BEGIN)
    finish = page.index(HERO_END) + len(HERO_END)
    fresh = render_hero(data["hero_transcript"])
    if page[start:finish] == fresh:
        return False
    HOME.write_text(page[:start] + fresh + page[finish:], encoding="utf-8")
    return True


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="fail if the committed fixture is missing or stale")
    args = ap.parse_args(argv)

    fresh = build()

    if args.check:
        if not OUT.exists():
            print(f"GATEWAY FAIL: {OUT.relative_to(ROOT)} does not exist. "
                  "Run scripts/build_gateway_fixture.py.", file=sys.stderr)
            return 1
        committed = json.loads(OUT.read_text(encoding="utf-8"))
        # `generated_at`-style fields would churn; compare only what the page shows.
        if (committed.get("scenarios") != fresh["scenarios"]
                or committed.get("hero_transcript") != fresh["hero_transcript"]):
            print("GATEWAY FAIL: assets/data/gateway-trace.json no longer matches what "
                  "the engine produces. Re-run scripts/build_gateway_fixture.py and "
                  "commit the result.", file=sys.stderr)
            return 1
        page = PAGE.read_text(encoding="utf-8")
        if BEGIN not in page or END not in page:
            print(f"GATEWAY FAIL: {PAGE.name} has lost its generated block.", file=sys.stderr)
            return 1
        rendered = page[page.index(BEGIN):page.index(END) + len(END)]
        if rendered != render_html(fresh):
            print("GATEWAY FAIL: the Trust Gateway markup in specification.html no longer "
                  "matches the engine's output. Re-run scripts/build_gateway_fixture.py "
                  "and commit the result.", file=sys.stderr)
            return 1
        home = HOME.read_text(encoding="utf-8")
        if HERO_BEGIN not in home or HERO_END not in home:
            print(f"GATEWAY FAIL: {HOME.name} has lost its generated hero block.", file=sys.stderr)
            return 1
        hero_block = home[home.index(HERO_BEGIN):home.index(HERO_END) + len(HERO_END)]
        if hero_block != render_hero(fresh["hero_transcript"]):
            print("GATEWAY FAIL: the hero transcript in index.html no longer matches the "
                  "engine's output. Re-run scripts/build_gateway_fixture.py and commit the "
                  "result.", file=sys.stderr)
            return 1
        turns = sum(len(s["turns"]) for s in fresh["scenarios"])
        print(f"GATEWAY PASS: fixture and page match the engine "
              f"({len(fresh['scenarios'])} scenarios, {turns} turns; hero transcript current)")
        return 0

    fresh["source_commit"] = _commit()
    OUT.write_text(json.dumps(fresh, indent=2) + "\n", encoding="utf-8")
    changed = inject(fresh)
    inject_hero(fresh)
    turns = sum(len(s["turns"]) for s in fresh["scenarios"])
    print(f"Wrote {OUT.relative_to(ROOT)} — {len(fresh['scenarios'])} scenarios, {turns} turns")
    print(f"{PAGE.name}: generated block " + ("updated" if changed else "already current"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
