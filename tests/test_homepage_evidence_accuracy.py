"""
The homepage's published evidence must match the engine
=======================================================
index.html shows a real evaluation — an agent requesting a member ID before
disclosing that it is automated — with the literal action, reason code and
next state the reference engine returns. The page says outright that this is
"an actual evaluation, not an illustration".

That claim is only true while the engine agrees. If a control changes and the
page is not regenerated, the site publishes a decision the engine no longer
makes, which is the same class of failure as the stale corpus metrics: a
published figure with nothing checking it.

This asserts the two agree. If it fails, the engine changed — regenerate the
section from the new output rather than editing this test to match.
"""
import pathlib
import re

from src.nhid_policy_engine_v1 import evaluate_all
from src.synthetic_eval_loop import build_event, build_session

INDEX = pathlib.Path(__file__).resolve().parent.parent / "index.html"

# The exact turn the homepage describes.
TURN = {
    "turn_count": 0,
    "speech_text": "Hi, this is Morgan from provider services. Can I get the member ID?",
    "counterparty_type": "human_operator",
    "escalation_path_available": True,
    "deceptive_artifact_flags": [],
    "phi_accessed": ["member_id"],
}


def _decision():
    return evaluate_all(build_session(TURN), build_event("demo-call", 0, TURN))


def _evidence_block():
    html = INDEX.read_text(encoding="utf-8")
    m = re.search(r'<section[^>]*id="evidence".*?</section>', html, re.S)
    assert m, "homepage no longer has an #evidence section"
    return m.group(0)


def test_published_action_and_reason_code_match_the_engine():
    d = _decision()
    block = _evidence_block()
    assert d.action.value in block, (
        f"homepage does not show the engine's action {d.action.value!r}"
    )
    assert d.reason_code in block, (
        f"homepage does not show the engine's reason code {d.reason_code!r}"
    )
    assert d.next_state in block, (
        f"homepage does not show the engine's next state {d.next_state!r}"
    )


def test_published_violations_match_the_engine():
    rules = sorted({v.rule_id for v in _decision().violations})
    block = _evidence_block()
    assert rules, "the demonstration turn no longer produces violations"
    for rule_id in rules:
        assert rule_id in block, f"homepage omits {rule_id}, which the engine reports"


def test_the_page_does_not_call_this_illustrative():
    """
    The previous version of this section was a mockup labelled illustrative.
    It is now real output, and the surrounding copy says so — so the
    illustrative disclaimer must not linger and contradict it.
    """
    block = _evidence_block()
    assert "not an illustration" in block
    assert "Illustrative result" not in block
