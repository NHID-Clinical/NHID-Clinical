"""Replay one call through the controls, turn by turn: the one place that does it.

Scoring a whole call means running every turn through ``evaluate_all`` while
carrying one fact across turns: whether the agent had already disclosed its
non-human identity on an EARLIER turn. The engine reads that as
``session["disclosure_established_prior"]`` and, when a harness leaves it out,
assumes ``True``, the permissive reading (``src/nhid_policy_engine_v1.py``).
A harness that forgets to set it fails open, silently: the same-turn PDX-01
rule (disclosure and a protected-data request in one breath) and IDG-01's
human-persona check never run.

That loop used to be written separately by each harness, and the Tier 0 pilot
replay (``src/pilot_measure.py``) was one that forgot. Harnesses now hand their
turns here and get one result per turn back.

Two shapes of input come here:

* ``replay_call``: eval-loop turn dicts (corpora, pilot captures, red-team
  scenarios, the site fixtures).
* ``replay_transcript``: call-progress turns (speaker, text, turn_index), as a
  live platform reports them. The ElevenLabs post-call handler uses it.

Both are for an agent that PLACES the call. ``orient_calling_agent`` gives each
engine slot the party it describes for such an agent. ``replay_transcript`` and
the pre-utterance gate (``functions.handler.gate_turn``) both use it, so the
orientation is written once.

Deliberately NOT routed through here: ``synthetic_eval_loop.evaluate_conversation``,
which feeds the pinned Fabricate baseline (``scripts/check_baseline.py``) and
keeps the permissive default by design until a §9.1 decision moves it.

Offline, standard library only: listed in ``GUARDED`` in
``scripts/check_offline_kit.py``, because the pilot kit imports it.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, Iterator, List, Optional, Sequence, Tuple

from adapters.call_progress_adapter import to_nhid_event
from src.nhid_policy_engine_v1 import PolicyDecision, _phi_fields_requested, evaluate_all
from src.synthetic_eval_loop import (
    build_event, build_session, carry_disclosure_forward, extract_rule_ids,
)


@dataclass(frozen=True)
class ReplayedTurn:
    """One turn of a replayed call, with everything the engine saw and said."""

    index: int
    turn: dict
    session: dict
    event: dict
    decision: PolicyDecision

    @property
    def rule_ids(self) -> List[str]:
        return extract_rule_ids(self.decision.violations)


def replay_call(turns: Sequence[dict[str, Any]], *, conversation_id: str,
                positions: Optional[Iterable[int]] = None) -> List[ReplayedTurn]:
    """Run every turn of one call through ``evaluate_all``, in order.

    ``turns`` are eval-loop turn dicts (see ``synthetic_eval_loop.build_session``
    and ``build_event``). Disclosure is carried forward to later turns, and each
    turn is told whether disclosure was established before it. The input is not
    modified. ``positions`` overrides the turn index given to the engine, for a
    caller that replays only some turns of a longer transcript.
    """
    carried = carry_disclosure_forward(list(turns))
    indexes = list(positions) if positions is not None else list(range(len(carried)))
    if len(indexes) != len(carried):
        raise ValueError("positions must name one index per turn")
    results: List[ReplayedTurn] = []
    for index, turn in zip(indexes, carried):
        session = build_session(turn)
        event = build_event(conversation_id, index, turn)
        results.append(ReplayedTurn(index, turn, session, event, evaluate_all(session, event)))
    return results


def orient_calling_agent(session: dict, event: dict, *, agent_text: str,
                         disclosed_before: bool, heard: Optional[str] = None) -> None:
    """Give each engine slot the party it describes, for an agent that CALLS.

    The call-progress adapter was written receiver-side: it looks for protected
    data only in the human's words. Here the agent is the caller, so:

    * the agent's own words are the data request PDX-01 gates, in the engine's
      field names, and the identity assertion DBC-01 judges;
    * ``heard``, when given, is what the payer's representative said, where
      EIT-01 looks for a request for a person (the gate passes it; a replayed
      transcript already has the representative's turns as their own turns);
    * the harness, which knows the call's history, tells PDX-01 whether
      disclosure was established on an earlier turn.

    Computes no decision of its own. Mutates ``session`` and ``event``.
    """
    governance = event["healthcare_governance"]
    governance["phi_accessed"] = sorted(_phi_fields_requested(agent_text, []))
    governance["identity_assertion_text"] = agent_text
    if heard is not None:
        event["input_payload"]["speech_text"] = heard
    session["disclosure_established_prior"] = disclosed_before


TranscriptStep = Tuple[dict, dict, dict, PolicyDecision, Dict[str, Any]]


def replay_transcript(turns: Sequence[dict[str, Any]], *,
                      timestamp: Optional[Callable[[dict], Optional[str]]] = None,
                      ) -> Iterator[TranscriptStep]:
    """Replay a calling agent's call-progress transcript, turn by turn.

    Each turn is ``{session_id, turn_index, speaker, text, interrupted}``.
    ``speaker`` is ``"agent"`` for the caller-agent and anything else for the
    payer's representative who answered. The adapter's ``session_state``
    carries the disclosure forward, agent turns are oriented with
    ``orient_calling_agent``, and ``timestamp(turn)`` (optional) supplies each
    turn's ISO time.

    Yields ``(turn, session, event, decision, session_state)``.
    ``session_state`` is the state AFTER the turn, as a store would keep it.
    """
    session_state: Dict[str, Any] = {
        "turn_count": 0,
        "disclosure_timestamp": None,
        "escalation_available": True,
    }
    for turn in turns:
        disclosed_before = session_state["disclosure_timestamp"] is not None
        body: Dict[str, Any] = {
            "session_id": turn["session_id"],
            "turn_index": turn["turn_index"],
            "speaker": turn["speaker"],
            "text": turn["text"],
            "interrupted": turn.get("interrupted", False),
            "session_state": session_state,
        }
        iso = timestamp(turn) if timestamp is not None else None
        if iso:
            body["timestamp"] = iso
        session, event = to_nhid_event(body)
        if turn["speaker"] == "agent":
            orient_calling_agent(session, event, agent_text=turn["text"],
                                 disclosed_before=disclosed_before)
        else:
            session["disclosure_established_prior"] = disclosed_before
        decision = evaluate_all(session, event)
        session_state = dict(session_state)
        session_state["turn_count"] = turn["turn_index"] + 1
        session_state["disclosure_timestamp"] = event["healthcare_governance"]["disclosure_timestamp"]
        yield turn, session, event, decision, session_state
