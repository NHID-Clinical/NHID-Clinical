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

from src.nhid_policy_engine_v1 import evaluate_all  # noqa: E402
from synthetic_eval_loop import (  # noqa: E402
    build_event,
    build_session,
    carry_disclosure_forward,
)

CORPUS = ROOT / "tests" / "evaluation_corpus_v1.json"
OUT = ROOT / "assets" / "data" / "gateway-trace.json"
PAGE = ROOT / "specification.html"
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
            "title": scenario.get("title", scenario_id),
            "expected_violations": scenario.get("expected_violations") or [],
            "note": SPEAKER_NOTE[scenario_id],
            "turns": turns,
        })
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
        if committed.get("scenarios") != fresh["scenarios"]:
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
        turns = sum(len(s["turns"]) for s in fresh["scenarios"])
        print(f"GATEWAY PASS: fixture and page match the engine "
              f"({len(fresh['scenarios'])} scenarios, {turns} turns)")
        return 0

    fresh["source_commit"] = _commit()
    OUT.write_text(json.dumps(fresh, indent=2) + "\n", encoding="utf-8")
    changed = inject(fresh)
    turns = sum(len(s["turns"]) for s in fresh["scenarios"])
    print(f"Wrote {OUT.relative_to(ROOT)} — {len(fresh['scenarios'])} scenarios, {turns} turns")
    print(f"{PAGE.name}: generated block " + ("updated" if changed else "already current"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
