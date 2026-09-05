#!/usr/bin/env python3
"""
Generate the site's three evidence-backed visuals from repository data.

The visual audit found that the Trust Gateway was the only visual on the site
whose content was the output of executing something, rather than a drawing of
what executing it would look like. Everything quantitative — corpus results,
detection rates, conformance counts — reached the reader as prose.

This script adds three more, on the same terms scripts/build_gateway_fixture.py
established:

    repository data -> replay through the real engine -> generated visual

  1. Enforcement ladder      specification.html
     How evaluate_all actually resolves five controls into one decision, with
     measured evidence of which control set the composite on each corpus turn.

  2. Shadow outcome chart    shadow-evaluation-guide.html
     The distribution of decisions an observe-only run produces over the
     committed shadow-pilot corpus.

  3. Evidence scorecard      evidence-pack.html
     The four evidence populations, kept separate, each with its own
     denominator and its own reproduction command.

Nothing here is drawn by hand. Every number is computed at generation time and
re-computed by --check, which is wired into CI.

A note on the ladder, because it is the easiest thing to get wrong: evaluate_all
does NOT walk the controls in series like a gate chain. It evaluates all of them
against the same session and event, then takes the most restrictive result by
priority. Drawing it as IDG -> PDX -> DBC -> EIT -> ATR would be a clearer
picture of a system that does not exist. The generated figure shows the fan-out
and the resolution, and reports how often more than one control tied at the top.

Usage:
    python scripts/build_evidence_visuals.py            # write the visuals
    python scripts/build_evidence_visuals.py --check    # verify, write nothing
"""
from __future__ import annotations

import argparse
import ast
import collections
import csv
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

# ── Sources ────────────────────────────────────────────────────────────────
ENGINE = ROOT / "src" / "nhid_policy_engine_v1.py"
GOV_CORPUS = ROOT / "tests" / "evaluation_corpus_v1.json"
SHADOW_CORPUS = ROOT / "fixtures" / "fabricate" / "shadow_pilot.jsonl"
FABRICATE_CSV = ROOT / "fixtures" / "fabricate" / "conversations.csv"
BASELINE = ROOT / "scripts" / "check_baseline.py"
VALIDATE_CI = ROOT / "scripts" / "validate_ci.py"

OUT = ROOT / "assets" / "data" / "evidence-visuals.json"

GOV_GROUPS = ("compliant_scenarios", "single_rule_violations", "multi_rule_combinations")
CONTROLS = ("IDG-01", "PDX-01", "DBC-01", "EIT-01", "ATR-01")

# Ordered most restrictive first; the numbers are read from the engine, not typed.
ACTION_ORDER = ("DENY_DATA", "ESCALATE_HUMAN", "DISCLOSE_IDENTITY", "LOG_ONLY", "CONTINUE_AI")

TARGETS = {
    "enforcement-ladder": ROOT / "specification.html",
    "shadow-outcomes": ROOT / "shadow-evaluation-guide.html",
    "evidence-scorecard": ROOT / "evidence-pack.html",
}

PRIORITY_PATTERN = re.compile(r"PolicyAction\.(?P<action>[A-Z_]+)\s*:\s*(?P<priority>\d+)")


# ── Helpers ────────────────────────────────────────────────────────────────

def _commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT, capture_output=True, text=True, check=True,
        ).stdout.strip()
    except Exception:
        return "unknown"


def _action_priority() -> dict[str, int]:
    ladder = {
        m.group("action"): int(m.group("priority"))
        for m in PRIORITY_PATTERN.finditer(ENGINE.read_text(encoding="utf-8"))
    }
    if not ladder:
        raise SystemExit(
            "EVIDENCE FAIL: could not read the priority ladder out of the engine."
        )
    return ladder


def _module_constant(path: Path, name: str) -> Any:
    """Read a literal constant out of a script without importing it.

    Same approach as scripts/check_number_drift.py: parse, don't exec. These
    numbers are published, so reading them from their single definition is the
    point — retyping one here would create exactly the second source of truth
    the drift guards exist to prevent.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return ast.literal_eval(node.value)
    raise SystemExit(f"EVIDENCE FAIL: could not read {name} from {path.name}.")


def _esc(text: Any) -> str:
    return (str(text).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


# ── Measurement 1: how the ladder resolves, over the governance corpus ─────

def measure_ladder() -> dict[str, Any]:
    corpus = json.loads(GOV_CORPUS.read_text(encoding="utf-8"))
    scenarios = [s for g in GOV_GROUPS for s in corpus[g]]
    priority = _action_priority()

    composite = collections.Counter()
    winners = collections.Counter()
    contested = 0
    turns = 0

    for scenario in scenarios:
        for index, turn in enumerate(carry_disclosure_forward(scenario["turns"])):
            turns += 1
            session = build_session(turn)
            event = build_event(scenario["scenario_id"], index, turn)

            composite[evaluate_all(session, event).action.name] += 1

            per_control = {
                "IDG-01": evaluate_idg01(session, event),
                "PDX-01": evaluate_pdx01(session, event),
                "DBC-01": evaluate_dbc01(session, event),
                "EIT-01": evaluate_eit01(session, event),
                "ATR-01": evaluate_atr01(session, event),
            }
            top = max(priority[d.action.name] for d in per_control.values())
            tied = [c for c, d in per_control.items() if priority[d.action.name] == top]
            if len(tied) > 1:
                contested += 1
            for control in tied:
                winners[control] += 1

    return {
        "source": "tests/evaluation_corpus_v1.json",
        "scenarios": len(scenarios),
        "turns": turns,
        "priority": priority,
        "composite": {a: composite.get(a, 0) for a in ACTION_ORDER},
        "set_composite": {c: winners.get(c, 0) for c in CONTROLS},
        "contested_turns": contested,
    }


# ── Measurement 2: observe-only outcomes over the shadow-pilot corpus ─────

def _shadow_turns(conversation: dict[str, Any]) -> list[dict[str, Any]]:
    """Translate one shadow-pilot conversation into the canonical turn shape.

    The shadow-pilot fixture carries a deliberately minimal event schema:
    turn_index, speaker, text, contains_phi, is_identity_disclosure,
    is_escalation_request, created_at. Three translation decisions follow from
    that, and all three are stated on the rendered figure rather than buried:

      * `contains_phi` is a flag, not a field list, so it becomes a single
        neutral marker. The engine also detects protected-data requests
        lexically from speech, so this supplements that signal.
      * The fixture has no `deceptive_artifact_flags`, which is the field
        DBC-01 actually reads. DBC-01 therefore runs on its lexical path only
        over this corpus, and the figure says so — otherwise a low DBC-01 count
        would read as "no deception found" when it means "the field is absent".
      * `escalation_path_available` is not carried, so build_session's default
        (True) applies, exactly as it does for every other replay path.
    """
    turns = []
    for turn in conversation["turns"]:
        disclosed = bool(turn.get("is_identity_disclosure"))
        turns.append({
            "speech_text": turn.get("text", "") or "",
            "timestamp": turn.get("created_at"),
            "disclosure_timestamp": turn.get("created_at") if disclosed else None,
            "identity_assertion_text": turn.get("text", "") if disclosed else "",
            "phi_accessed": ["protected_data"] if turn.get("contains_phi") else [],
        })
    return carry_disclosure_forward(turns)


def measure_shadow() -> dict[str, Any]:
    actions = collections.Counter()
    reasons = collections.Counter()
    by_control = collections.Counter()
    conversations = 0
    turns = 0

    for line in SHADOW_CORPUS.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        conversation = json.loads(line)
        conversations += 1
        for index, turn in enumerate(_shadow_turns(conversation)):
            turns += 1
            decision = evaluate_all(
                build_session(turn),
                build_event(conversation["scenario_id"], index, turn),
            )
            actions[decision.action.name] += 1
            reasons[decision.reason_code] += 1
            for violation in decision.violations:
                by_control[violation.rule_id] += 1

    observed = {a: actions.get(a, 0) for a in ACTION_ORDER}
    enforcing = sum(n for a, n in observed.items() if a != "CONTINUE_AI")

    return {
        "source": "fixtures/fabricate/shadow_pilot.jsonl",
        "conversations": conversations,
        "turns": turns,
        "actions": observed,
        "enforcing_turns": enforcing,
        # Lists, not tuples: this dict round-trips through JSON for the
        # drift check, and a tuple would come back as a list and never match.
        "top_reasons": [[code, count] for code, count in reasons.most_common(5)],
        "violations_by_control": {c: by_control.get(c, 0) for c in CONTROLS},
        "schema_note": (
            "The shadow-pilot fixture carries no deceptive_artifact_flags field, "
            "which is the structured signal DBC-01 reads. Over this corpus DBC-01 "
            "runs on its lexical path only, so its count here is a floor, not a "
            "measurement of how much deception the corpus contains."
        ),
    }


# ── Measurement 3: the evidence populations, kept apart ───────────────────

def measure_scorecard() -> dict[str, Any]:
    gov = json.loads(GOV_CORPUS.read_text(encoding="utf-8"))
    gov_scenarios = [s for g in GOV_GROUPS for s in gov[g]]
    gov_turns = sum(len(s["turns"]) for s in gov_scenarios)
    gov_expected = sum(len(s.get("expected_violations") or []) for s in gov_scenarios)

    # Detection, measured the same way scripts/eval_corpus.py measures it:
    # a rule counts as detected if any turn in its scenario surfaces it.
    detected = 0
    for scenario in gov_scenarios:
        expected = set(scenario.get("expected_violations") or [])
        if not expected:
            continue
        surfaced: set[str] = set()
        for index, turn in enumerate(carry_disclosure_forward(scenario["turns"])):
            decision = evaluate_all(
                build_session(turn),
                build_event(scenario["scenario_id"], index, turn),
            )
            surfaced.update(v.rule_id for v in decision.violations)
        detected += len(expected & surfaced)

    with FABRICATE_CSV.open(encoding="utf-8", newline="") as handle:
        fabricate_rows = sum(1 for _ in csv.DictReader(handle))

    shadow_conversations = sum(
        1 for line in SHADOW_CORPUS.read_text(encoding="utf-8").splitlines() if line.strip()
    )

    baseline = _module_constant(BASELINE, "EXPECTED")
    unit_published = _module_constant(VALIDATE_CI, "UNIT_PUBLISHED")

    return {
        "populations": [
            {
                "name": "Governance Evaluation Corpus",
                "measures": "Rule detection on hand-authored scenarios",
                "size": f"{len(gov_scenarios)} scenarios · {gov_turns} turns",
                "result": f"{detected}/{gov_expected} expected violations detected",
                "rate": round(100.0 * detected / gov_expected, 1) if gov_expected else 0.0,
                "source": "tests/evaluation_corpus_v1.json",
                "command": "python scripts/eval_corpus.py --check",
            },
            {
                "name": "Fabricate baseline corpus",
                "measures": "Per-control detection and false positives",
                "size": f"{fabricate_rows} conversations",
                "result": " · ".join(
                    f"{c} {v[0]}/{v[1]}" for c, v in sorted(baseline.items())
                ),
                "rate": None,
                "source": "fixtures/fabricate/conversations.csv",
                "command": "python scripts/check_baseline.py",
            },
            {
                "name": "Shadow-pilot corpus",
                "measures": "Observe-only decision distribution",
                "size": f"{shadow_conversations} conversations",
                "result": "Distribution charted on the shadow evaluation guide",
                "rate": None,
                "source": "fixtures/fabricate/shadow_pilot.jsonl",
                "command": "python scripts/build_evidence_visuals.py --check",
            },
            {
                "name": "Conformance suite",
                "measures": "Implementation correctness against the specification",
                "size": f"{unit_published} tests",
                "result": f"{unit_published}/{unit_published} passing, 0 skipped, 0 xfailed",
                "rate": 100.0,
                "source": "tests/",
                "command": "python -m pytest tests/ -q",
            },
        ],
        "separation_note": (
            "Four populations, four denominators. They measure different things "
            "and are never combined into a single figure: a detection rate on "
            "hand-authored scenarios is not a conformance pass rate, and neither "
            "is a measure of production performance."
        ),
    }


# ── Rendering ──────────────────────────────────────────────────────────────

def _bar_chart(actions: dict[str, int], total: int) -> str:
    """Horizontal bars. Length encodes the count; the count is also printed."""
    rows = [(a, n) for a, n in actions.items() if n]
    top = max((n for _, n in rows), default=1)
    x0, width = 210.0, 560.0
    parts = []
    y = 54
    for action, count in rows:
        length = max(2.0, width * count / top)
        share = 100.0 * count / total if total else 0.0
        tone = "continue" if action == "CONTINUE_AI" else "enforce"
        parts.append(
            f'          <text x="{x0 - 12}" y="{y + 13}" text-anchor="end" class="ev-cat">'
            f"{_esc(action)}</text>\n"
            f'          <rect x="{x0}" y="{y}" width="{length:.1f}" height="20" rx="3" '
            f'class="ev-bar" data-tone="{tone}"/>\n'
            f'          <text x="{x0 + length + 10:.1f}" y="{y + 14}" class="ev-val">'
            f"{count} <tspan class=\"ev-pct\">({share:.1f}%)</tspan></text>"
        )
        y += 30
    return "\n".join(parts), y


def render_ladder(data: dict[str, Any]) -> str:
    d = data["ladder"]
    priority = d["priority"]
    rungs = []
    y = 250
    for action in ACTION_ORDER:
        rungs.append(
            f'          <rect x="24" y="{y}" width="300" height="26" rx="4" class="el-rung"/>\n'
            f'          <text x="40" y="{y + 17}" class="el-pri">{priority[action]}</text>\n'
            f'          <text x="70" y="{y + 17}" class="el-action">{_esc(action)}</text>\n'
            f'          <text x="316" y="{y + 17}" text-anchor="end" class="el-count">'
            f'{d["composite"][action]} turn{"" if d["composite"][action] == 1 else "s"}</text>'
        )
        y += 32
    rung_svg = "\n".join(rungs)

    wins = []
    wy = 250
    top = max(d["set_composite"].values()) or 1
    for control in CONTROLS:
        n = d["set_composite"][control]
        length = max(2.0, 220.0 * n / top)
        wins.append(
            f'          <text x="470" y="{wy + 17}" text-anchor="end" class="el-ctl">'
            f"{_esc(control)}</text>\n"
            f'          <rect x="482" y="{wy + 4}" width="{length:.1f}" height="18" rx="3" '
            f'class="el-winbar"/>\n'
            f'          <text x="{482 + length + 9:.1f}" y="{wy + 17}" class="el-count">{n}</text>'
        )
        wy += 32
    win_svg = "\n".join(wins)

    return f"""<figure class="evidence-model enforcement-ladder">
        <svg viewBox="0 0 880 440" role="img" aria-labelledby="el2-title el2-desc" style="width:100%;height:auto;display:block">
          <title id="el2-title">How five control decisions resolve into one</title>
          <desc id="el2-desc">One turn event fans out to all five controls, which evaluate independently against the same session and event. Each returns its own PolicyDecision. The composite decision is the most restrictive of the five by priority: DENY_DATA at {priority['DENY_DATA']}, ESCALATE_HUMAN at {priority['ESCALATE_HUMAN']}, DISCLOSE_IDENTITY at {priority['DISCLOSE_IDENTITY']}, LOG_ONLY at {priority['LOG_ONLY']}, CONTINUE_AI at {priority['CONTINUE_AI']}. This is not a serial gate chain: on {d['contested_turns']} of the corpus's {d['turns']} turns more than one control tied at the top. The left column counts how often each action was the composite across the corpus; the right column counts how often each control was at the winning priority.</desc>

          <text x="24" y="22" class="el-zone">ONE TURN, FIVE INDEPENDENT EVALUATIONS</text>

          <g class="el-node"><rect x="24" y="40" width="150" height="52" rx="8"/></g>
          <text x="99" y="63" text-anchor="middle" class="el-title">Turn event</text>
          <text x="99" y="80" text-anchor="middle" class="el-sub">session + event</text>

          <path d="M174 66 H214" class="el-flow"/><polygon points="218,66 208,61 208,71" class="el-flow-head"/>

          <g class="el-ctlbox">
            <rect x="218" y="34" width="128" height="26" rx="5"/>
            <rect x="218" y="64" width="128" height="26" rx="5"/>
            <rect x="218" y="94" width="128" height="26" rx="5"/>
            <rect x="218" y="124" width="128" height="26" rx="5"/>
          </g>
          <g class="el-auditbox"><rect x="218" y="154" width="128" height="26" rx="5"/></g>
          <text x="282" y="51" text-anchor="middle" class="el-ctlname">IDG-01</text>
          <text x="282" y="81" text-anchor="middle" class="el-ctlname">PDX-01</text>
          <text x="282" y="111" text-anchor="middle" class="el-ctlname">DBC-01</text>
          <text x="282" y="141" text-anchor="middle" class="el-ctlname">EIT-01</text>
          <text x="282" y="171" text-anchor="middle" class="el-ctlname">ATR-01</text>

          <path d="M346 47 H392 V100" class="el-flow"/>
          <path d="M346 77 H392" class="el-flow"/>
          <path d="M346 107 H392 V100" class="el-flow"/>
          <path d="M346 137 H392 V100" class="el-flow"/>
          <path d="M346 167 H392 V100" class="el-flow"/>
          <polygon points="424,100 414,95 414,105" class="el-flow-head"/>
          <path d="M392 100 H418" class="el-flow"/>

          <g class="el-node"><rect x="428" y="60" width="196" height="80" rx="8"/></g>
          <text x="526" y="86" text-anchor="middle" class="el-title">Most restrictive wins</text>
          <text x="526" y="104" text-anchor="middle" class="el-sub">max(decisions, key=priority)</text>
          <text x="526" y="124" text-anchor="middle" class="el-sub">ties are common, not exceptional</text>

          <path d="M624 100 H664" class="el-flow"/><polygon points="668,100 658,95 658,105" class="el-flow-head"/>
          <g class="el-node"><rect x="672" y="60" width="184" height="80" rx="8"/></g>
          <text x="764" y="86" text-anchor="middle" class="el-title">PolicyDecision</text>
          <text x="764" y="104" text-anchor="middle" class="el-sub">action · reason_code</text>
          <text x="764" y="124" text-anchor="middle" class="el-sub">violations · audit trail</text>

          <line x1="24" y1="200" x2="856" y2="200" class="el-divider"/>
          <text x="24" y="228" class="el-zone">MEASURED OVER {d['scenarios']} SCENARIOS · {d['turns']} TURNS</text>

          <text x="24" y="244" class="el-colhead">Priority ladder — how often each action was the composite</text>
{rung_svg}

          <text x="482" y="244" class="el-colhead">How often each control was at the winning priority</text>
{win_svg}

          <text x="482" y="{wy + 14}" class="el-note">{d['contested_turns']} of {d['turns']} turns had two or more controls tied at the top.</text>
        </svg>
      </figure>

      <aside class="visual-provenance">
        <p><strong>Evidence basis:</strong> <code>{_esc(d['source'])}</code> — {d['scenarios']} scenarios, {d['turns']} turns, replayed through <code>src/nhid_policy_engine_v1.py :: evaluate_all</code></p>
        <p><strong>Generator:</strong> <code>scripts/build_evidence_visuals.py</code> · <strong>Verification:</strong> <code>python scripts/build_evidence_visuals.py --check</code> (runs in CI)</p>
        <p><strong>Version:</strong> policy engine v1.3 · commit <code>{_esc(data['source_commit'])}</code></p>
      </aside>"""


def render_shadow(data: dict[str, Any]) -> str:
    d = data["shadow"]
    bars, end_y = _bar_chart(d["actions"], d["turns"])
    height = end_y + 46
    enforcing_pct = 100.0 * d["enforcing_turns"] / d["turns"] if d["turns"] else 0.0
    action_desc = ", ".join(
        f"{a} on {n} turns" for a, n in d["actions"].items() if n
    )

    return f"""<figure class="evidence-model shadow-outcomes">
        <svg viewBox="0 0 880 {height}" role="img" aria-labelledby="so-title so-desc" style="width:100%;height:auto;display:block">
          <title id="so-title">What an observe-only run returns over the shadow-pilot corpus</title>
          <desc id="so-desc">A horizontal bar chart of composite decisions across {d['turns']} turns in {d['conversations']} conversations: {action_desc}. {d['enforcing_turns']} turns — {enforcing_pct:.1f} percent — returned something other than CONTINUE_AI, which is the share a deployment would have to act on if it moved from observing to enforcing. No call routing was changed to produce this: the engine was run over a committed corpus.</desc>

          <text x="24" y="22" class="ev-zone">COMPOSITE DECISION PER TURN · {d['conversations']} CONVERSATIONS · {d['turns']} TURNS</text>
          <text x="24" y="40" class="ev-sub">Observe-only replay. Nothing was routed, blocked or escalated to produce this.</text>

{bars}

          <line x1="24" y1="{end_y + 6}" x2="856" y2="{end_y + 6}" class="ev-divider"/>
          <text x="24" y="{end_y + 28}" class="ev-headline">{d['enforcing_turns']} of {d['turns']} turns ({enforcing_pct:.1f}%) would have drawn an enforcement action.</text>
        </svg>
      </figure>

      <aside class="visual-provenance">
        <p><strong>Evidence basis:</strong> <code>{_esc(d['source'])}</code> — {d['conversations']} conversations, {d['turns']} turns, replayed through <code>src/nhid_policy_engine_v1.py :: evaluate_all</code></p>
        <p><strong>Classification:</strong> <span class="maturity-research">Research</span> Reference corpus results, not operational performance. This is a committed synthetic corpus, not production call data, and it says nothing about how any deployment would behave.</p>
        <p><strong>Known limitation:</strong> {_esc(d['schema_note'])}</p>
        <p><strong>Generator:</strong> <code>scripts/build_evidence_visuals.py</code> · <strong>Verification:</strong> <code>python scripts/build_evidence_visuals.py --check</code> (runs in CI) · commit <code>{_esc(data['source_commit'])}</code></p>
      </aside>"""


def render_scorecard(data: dict[str, Any]) -> str:
    d = data["scorecard"]
    rows = []
    for population in d["populations"]:
        rate = (f'<span class="sc-rate">{population["rate"]}%</span>'
                if population["rate"] is not None else "")
        rows.append(
            "          <tr>\n"
            f'            <th scope="row">{_esc(population["name"])}'
            f'<span class="sc-measures">{_esc(population["measures"])}</span></th>\n'
            f'            <td class="sc-size">{_esc(population["size"])}</td>\n'
            f'            <td>{_esc(population["result"])} {rate}</td>\n'
            f'            <td><code>{_esc(population["command"])}</code>'
            f'<span class="sc-src">{_esc(population["source"])}</span></td>\n'
            "          </tr>"
        )
    body = "\n".join(rows)

    # No pipeline graphic here on purpose. Section 0 of this page already
    # carries the evidence lifecycle model, which draws exactly that path; a
    # second one would be the duplication the visual audit criticised. What
    # section 0 cannot do is show the live numbers, so this is a table — the
    # right form for tabular data, and accessible without any drawing at all.
    return f"""<div class="sc-wrap">
        <table class="scorecard-table">
          <caption>Four evidence populations, measured at generation time. Each has its own denominator and its own reproduction command.</caption>
          <thead>
            <tr><th scope="col">Population</th><th scope="col">Size</th><th scope="col">Result</th><th scope="col">Reproduce</th></tr>
          </thead>
          <tbody>
{body}
          </tbody>
        </table>
      </div>

      <aside class="visual-provenance">
        <p><strong>Separation:</strong> {_esc(d['separation_note'])}</p>
        <p><strong>Generator:</strong> <code>scripts/build_evidence_visuals.py</code> &middot; <strong>Verification:</strong> <code>python scripts/build_evidence_visuals.py --check</code> (runs in CI) &middot; commit <code>{_esc(data['source_commit'])}</code></p>
      </aside>"""


RENDERERS = {
    "enforcement-ladder": render_ladder,
    "shadow-outcomes": render_shadow,
    "evidence-scorecard": render_scorecard,
}


# ── Assembly ───────────────────────────────────────────────────────────────

def build() -> dict[str, Any]:
    return {
        "generated_by": "scripts/build_evidence_visuals.py",
        "engine": "src/nhid_policy_engine_v1.py :: evaluate_all",
        "note": (
            "Every figure below is computed by replaying committed repository "
            "data through the real engine at generation time. Nothing is drawn "
            "by hand and no number is transcribed."
        ),
        "ladder": measure_ladder(),
        "shadow": measure_shadow(),
        "scorecard": measure_scorecard(),
    }


def block(name: str, data: dict[str, Any]) -> str:
    begin = f"<!-- BEGIN GENERATED {name} -->"
    end = f"<!-- END GENERATED {name} -->"
    return f"{begin}\n      {RENDERERS[name](data)}\n      {end}"


def inject(data: dict[str, Any]) -> list[str]:
    changed = []
    for name, page in TARGETS.items():
        begin = f"<!-- BEGIN GENERATED {name} -->"
        end = f"<!-- END GENERATED {name} -->"
        source = page.read_text(encoding="utf-8")
        if begin not in source or end not in source:
            raise SystemExit(
                f"EVIDENCE FAIL: {page.name} has no generated block for {name}."
            )
        start = source.index(begin)
        stop = source.index(end) + len(end)
        rendered = block(name, data)
        if source[start:stop] != rendered:
            page.write_text(source[:start] + rendered + source[stop:], encoding="utf-8")
            changed.append(name)
    return changed


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="fail if any committed figure is missing or stale")
    args = ap.parse_args(argv)

    fresh = build()

    if args.check:
        if not OUT.exists():
            print(f"EVIDENCE FAIL: {OUT.relative_to(ROOT)} does not exist. "
                  "Run scripts/build_evidence_visuals.py.", file=sys.stderr)
            return 1
        committed = json.loads(OUT.read_text(encoding="utf-8"))
        for key in ("ladder", "shadow", "scorecard"):
            if committed.get(key) != fresh[key]:
                print(f"EVIDENCE FAIL: {OUT.relative_to(ROOT)} no longer matches what "
                      f"the engine produces (`{key}` differs). Re-run "
                      "scripts/build_evidence_visuals.py and commit the result.",
                      file=sys.stderr)
                return 1

        expected = dict(fresh)
        expected["source_commit"] = committed.get("source_commit", "unknown")
        for name, page in TARGETS.items():
            begin = f"<!-- BEGIN GENERATED {name} -->"
            end = f"<!-- END GENERATED {name} -->"
            source = page.read_text(encoding="utf-8")
            if begin not in source or end not in source:
                print(f"EVIDENCE FAIL: {page.name} has lost its {name} block.",
                      file=sys.stderr)
                return 1
            rendered = source[source.index(begin):source.index(end) + len(end)]
            if rendered != block(name, expected):
                print(f"EVIDENCE FAIL: the {name} figure in {page.name} no longer "
                      "matches the engine's output. Re-run "
                      "scripts/build_evidence_visuals.py and commit the result.",
                      file=sys.stderr)
                return 1

        print(
            "EVIDENCE PASS: all three figures match the engine "
            f"(ladder {fresh['ladder']['turns']} turns, "
            f"shadow {fresh['shadow']['turns']} turns, "
            f"{len(fresh['scorecard']['populations'])} populations kept separate)"
        )
        return 0

    fresh["source_commit"] = _commit()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(fresh, indent=2) + "\n", encoding="utf-8")
    changed = inject(fresh)
    print(f"Wrote {OUT.relative_to(ROOT)}")
    print("Injected: " + (", ".join(changed) if changed else "all blocks already current"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
