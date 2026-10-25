"""The home-page hero transcript is engine output for the words it shows.

The brief asked for the hero to replay corpus scenario nhid_ec_comp_001. That
scenario opens with the agent answering a member's call ("Thank you for
calling… your member information"), the reversed direction CLAUDE.md §1 rules
out. So the hero carries a caller-side script of its own, and what keeps it
honest is that every chip is the reference engine's own result for exactly
those words. These tests hold that line: the block on the page equals a fresh
run, the script never drifts back to the receiver side, and the caption says
what the chips do not mean.
"""
from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_gateway_fixture.py"
HOME = ROOT / "index.html"


@pytest.fixture(scope="module")
def gen():
    spec = importlib.util.spec_from_file_location("build_gateway_fixture", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def block(gen):
    html = HOME.read_text(encoding="utf-8")
    assert gen.HERO_BEGIN in html and gen.HERO_END in html, "index.html has lost the hero block"
    return html[html.index(gen.HERO_BEGIN):html.index(gen.HERO_END) + len(gen.HERO_END)]


def test_the_page_block_is_a_fresh_engine_run(gen, block):
    assert block == gen.render_hero(gen.build_hero()), (
        "the hero transcript on index.html is stale; run scripts/build_gateway_fixture.py"
    )


def test_every_chip_is_the_engines_reason_code_for_that_turn(gen, block):
    hero = gen.build_hero()
    for turn in hero["turns"]:
        if not turn["evaluated"]:
            continue
        for c in turn["controls"]:
            assert f'data-control="{c["rule_id"]}" data-reason="{c["reason_code"]}"' in block, (
                f"turn {turn['position']} {c['rule_id']} chip does not carry {c['reason_code']}"
            )


def test_the_disclosing_turn_confirms_and_the_request_turn_clears(gen):
    """The two things the hero exists to show. If the engine's codes change,
    regenerate the block; do not rewrite this to match."""
    hero = gen.build_hero()
    agent = [t for t in hero["turns"] if t["evaluated"]]
    first = {c["rule_id"]: c["reason_code"] for c in agent[0]["controls"]}
    last = {c["rule_id"]: c["reason_code"] for c in agent[-1]["controls"]}
    assert first["IDG-01"] == "IDG01_DISCLOSURE_CONFIRMED"
    assert last["PDX-01"] == "PDX01_GATE_CLEARED"
    for t in agent:
        assert t["audit"]["reason_code"] == "ATR01_AUDIT_COMPLETE"
        assert t["composite"]["action"] == "CONTINUE_AI"


def test_the_script_is_caller_side(gen):
    """The agent places the call. No turn may read as the agent answering one."""
    for turn in gen.HERO_TURNS:
        if turn["speaker"] != "agent":
            continue
        text = turn["speech_text"].lower()
        assert "calling" in text or "member id" in text
        assert not re.search(r"thank you for calling|thanks for calling|how can i help", text), (
            f"receiver-side wording in the hero script: {turn['speech_text']!r}"
        )
    speakers = [t["speaker"] for t in gen.HERO_TURNS]
    assert speakers[0] == "agent", "the agent speaks first: it placed the call"
    assert "representative" in speakers


def test_the_representative_turn_carries_no_chips(block):
    rep = re.search(r'<li class="ht-turn ht-rep".*?</li>', block, re.S)
    assert rep and "ht-chip" not in rep.group(0)


def test_no_dlg01_chip_and_the_caption_denies_authorization(block):
    assert 'data-control="DLG-01"' not in block
    assert "Disclosure is not authorization" in block
    assert "not a recorded call" in block
    assert '<span class="maturity-reference">' in block


def test_atr01_is_a_band_not_a_chip(block):
    assert 'data-control="ATR-01"' not in block
    assert '<p class="ht-audit"><b>ATR-01</b>' in block
    assert "Changes no behavior" in block
