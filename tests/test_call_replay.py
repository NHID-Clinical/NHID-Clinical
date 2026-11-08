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


# ── Call-progress transcripts and the calling-agent orientation ─────────────
# The ElevenLabs post-call handler and the pre-utterance gate used to orient
# the caller-agent's turns separately. They now share these.

from src.call_replay import orient_calling_agent, replay_transcript  # noqa: E402
from src.synthetic_eval_loop import extract_rule_ids  # noqa: E402

IDA_OPENING = "Hi, this is Ida, an automated AI assistant calling for a demonstration dental practice."
IDA_IDENTIFIERS = "The member ID is RVD-204-7731 and the claim number is 9921-0417. What's the status?"
REP = "Acme Health provider services, this is Dana. How can I help you?"


def _t(i, speaker, text):
    return {"session_id": "conv-1", "turn_index": i, "speaker": speaker,
            "text": text, "interrupted": False}


def _empty():
    return {}, {"healthcare_governance": {}, "input_payload": {"speech_text": "unchanged"}}


def test_orientation_puts_the_agents_words_where_pdx01_and_dbc01_read_them():
    session, event = _empty()
    orient_calling_agent(session, event, agent_text=IDA_IDENTIFIERS, disclosed_before=True)
    gov = event["healthcare_governance"]
    assert "member_id" in gov["phi_accessed"]
    assert gov["identity_assertion_text"] == IDA_IDENTIFIERS
    assert session["disclosure_established_prior"] is True
    assert event["input_payload"]["speech_text"] == "unchanged"  # no `heard`


def test_orientation_with_heard_puts_the_representative_in_speech_text():
    session, event = _empty()
    orient_calling_agent(session, event, agent_text="Okay.", disclosed_before=False, heard=REP)
    assert event["input_payload"]["speech_text"] == REP
    assert session["disclosure_established_prior"] is False


def test_transcript_replay_carries_disclosure_forward_only_after_it_happens():
    steps = list(replay_transcript([
        _t(0, "agent", IDA_OPENING), _t(1, "user", REP), _t(2, "agent", IDA_IDENTIFIERS)]))
    told = [s[1]["disclosure_established_prior"] for s in steps]
    assert told == [False, True, True]
    assert steps[-1][4]["turn_count"] == 3
    assert steps[-1][3].reason_code == "ATR01_AUDIT_COMPLETE"


def test_identifiers_before_disclosure_are_caught_in_a_transcript():
    steps = list(replay_transcript([_t(0, "user", REP), _t(1, "agent", IDA_IDENTIFIERS)]))
    _, session, event, decision, _ = steps[-1]
    assert session["disclosure_established_prior"] is False
    assert "member_id" in event["healthcare_governance"]["phi_accessed"]
    assert decision.reason_code == "PDX01_PHI_GATE_TRIGGERED"
    assert "PDX-01" in extract_rule_ids(decision.violations)


def test_transcript_replay_does_not_modify_its_input():
    turns = [_t(0, "agent", IDA_OPENING), _t(1, "agent", IDA_IDENTIFIERS)]
    before = copy.deepcopy(turns)
    list(replay_transcript(turns))
    assert turns == before
