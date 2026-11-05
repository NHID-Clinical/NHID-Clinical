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

Deliberately NOT routed through here: ``synthetic_eval_loop.evaluate_conversation``,
which feeds the pinned Fabricate baseline (``scripts/check_baseline.py``) and
keeps the permissive default by design until a §9.1 decision moves it.

Offline, standard library only: listed in ``GUARDED`` in
``scripts/check_offline_kit.py``, because the pilot kit imports it.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, List, Optional, Sequence

from src.nhid_policy_engine_v1 import PolicyDecision, evaluate_all
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
