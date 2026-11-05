"""
src/call_replay.py: the one place a whole call is replayed through the controls.

It must tell the engine, turn by turn, whether disclosure happened on an
earlier turn. The engine's default for a harness that does not say is the
permissive reading, so a harness that forgets fails open.
"""
from __future__ import annotations

import copy

import pytest

from src.call_replay import replay_call

DISCLOSE = "This is an automated system calling for a provider."


def _turn(text, disclosed=False, phi=None):
    turn = {"speech_text": text, "identity_assertion_text": text if disclosed else ""}
    if disclosed:
        turn["disclosure_timestamp"] = "2026-11-05T10:00:00Z"
    if phi:
        turn["phi_accessed"] = phi
    return turn


def test_each_turn_is_told_whether_disclosure_came_before_it():
    steps = replay_call([_turn(DISCLOSE, disclosed=True), _turn("Thanks."), _turn("Go on.")],
                        conversation_id="c")
    assert [s.session["disclosure_established_prior"] for s in steps] == [False, True, True]


def test_a_request_in_the_disclosing_turn_is_not_sequenced():
    steps = replay_call([_turn(DISCLOSE + " What is the member ID?", disclosed=True,
                               phi=["member_id"])], conversation_id="c")
    assert "PDX-01" in steps[0].rule_ids


def test_the_input_turns_are_not_modified():
    turns = [_turn(DISCLOSE, disclosed=True), _turn("Thanks.")]
    before = copy.deepcopy(turns)
    replay_call(turns, conversation_id="c")
    assert turns == before


def test_positions_set_the_index_the_engine_sees():
    steps = replay_call([_turn(DISCLOSE, disclosed=True), _turn("ok")],
                        conversation_id="c", positions=[1, 3])
    assert [s.index for s in steps] == [1, 3]
    with pytest.raises(ValueError):
        replay_call([_turn("a")], conversation_id="c", positions=[0, 1])
