"""Robot to robot: a caller-agent calls a payer whose own AI answers.

docs/agent-to-agent-calls.md. The canonical direction is unchanged
(CLAUDE.md §1): the caller-agent places the call and asks for a patient's
claim status. This is an extension in one respect only: the receiving party
is the payer's own AI agent, not a person.

Who is judged, and who enforces:

* The **controls judge the caller**, exactly as before. Every caller turn goes
  through the payer's gate (`functions.handler.gate_turn`) with
  `counterparty="ai_agent"`, so the engine also applies its bot-to-bot rule.
* The **payer's AI is the enforcement point**, not a subject of the controls.
  `PayerAgent` says it is automated before anything else, and it releases a
  claim status only when the gate allowed the turn *and* verified the
  caller's delegation (`delegation_checked`). A disclosed caller with no
  delegation is still refused: disclosure is not authorization. After one
  refusal, the protected part of the call is over.

`PayerAgent` is a deterministic reference, not a language model: its lines
are fixed, so a test can pin what it says. Nothing here places a real call;
`run_call` drives a whole call offline. Every identifier is fictional.
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

COUNTERPARTY = "ai_agent"

#: The payer's fictional claim records. A real payer agent reads its own system.
CLAIMS: Dict[str, str] = {
    "9921-0417": "Claim 9921-0417 was received on October 2 and is in process. "
                 "No payment has been issued yet.",
}
_CLAIM_NUMBER = re.compile(r"\b\d{4}-\d{4}\b")
#: The caller is asking about a member's records, with or without identifiers.
#: The gate only sees a data request when identifiers are spoken; the payer's AI
#: must also recognise the request itself, so that a caller who names no patient
#: is still refused until its delegation is verified.
_ASKS_ABOUT_A_MEMBER = re.compile(
    r"\b(claims?|eligibility|benefits|prior auth(orization)?s?|authorizations?)\b",
    re.IGNORECASE)
_ASKS_FOR_A_PERSON = re.compile(
    r"\b(speak|talk)\s+(to|with)\s+(a|an|someone|somebody)\s*"
    r"(person|human|representative|someone)?", re.IGNORECASE)


@dataclass
class PayerAgent:
    """The payer's reference AI agent, answering the provider line."""
    payer: str = "Acme Health"

    LINES = {
        "go_ahead": "Go ahead.",
        "which_claim": "Your delegation for this call is verified. Which claim number, please?",
        "no_delegation": "I can't discuss a member's records without a verified delegation "
                         "from the provider for this call. Please have the practice send one "
                         "and call back.",
        "refuse": "I can't share that on this call.",
        "after_refusal": "I've already declined to share member information on this call, "
                         "so I can't continue with that request.",
        "not_found": "I don't have a claim matching that number.",
        "transfer": "I'm transferring you to a person in provider services now.",
    }

    def greeting(self) -> str:
        return (f"{self.payer} provider services. This is an automated assistant, "
                "not a person. How can I help?")


@dataclass
class Turn:
    speaker: str                      # "payer_agent" or "caller"
    text: str
    gate: Optional[dict] = None       # the gate's answer for a caller turn
    released: bool = False            # a payer turn that disclosed protected data


@dataclass
class Call:
    scenario: str
    turns: List[Turn] = field(default_factory=list)
    outcome: str = "no_request"       # released | refused | escalated | no_request

    def render(self) -> str:
        names = {"payer_agent": "Payer AI", "caller": "Caller"}
        lines = [f"Scenario: {self.scenario}"]
        for t in self.turns:
            lines.append(f"{names[t.speaker]}: {t.text}")
            if t.gate:
                lines.append(f"    gate: {t.gate['action']} ({t.gate['reason_code']}), "
                             f"delegation checked: {t.gate.get('delegation_checked')}")
        lines.append(f"Outcome: {self.outcome}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {"scenario": self.scenario, "outcome": self.outcome,
                "turns": [{"speaker": t.speaker, "text": t.text, "released": t.released,
                           "gate": t.gate and {k: t.gate.get(k) for k in (
                               "action", "reason_code", "allowed", "counterparty",
                               "delegation_checked", "phi_requested")}}
                          for t in self.turns]}


@dataclass(frozen=True)
class Scenario:
    name: str
    summary: str
    caller_turns: Tuple[str, ...]
    presents_delegation: bool
    expected: str


DISCLOSE = "Hi, this is Ida, an automated AI assistant calling for a demonstration dental practice."
#: Ida asks without naming the patient. She volunteers no identifier: she is the
#: requester whose identity and authority are unproven (CLAUDE.md §1).
ASK = "I'm calling to ask about the status of a patient's claim."
#: Spoken only after the payer's AI has verified her delegation and asked which claim.
CLAIM_DETAIL = "The claim number is 9921-0417."
PA_ASK = "I'm calling to ask about the status of a patient's prior authorization."
PA_DETAIL = "The prior authorization number is PA-55120934."

SCENARIOS: Dict[str, Scenario] = {s.name: s for s in (
    Scenario("verified_ida", "Ida discloses and asks; once her delegation is verified and the "
             "payer's AI asks which claim, she names it.",
             (DISCLOSE, ASK, CLAIM_DETAIL), True, "released"),
    Scenario("undisclosed_bot", "A bot never says it is automated and asks about a claim.",
             ("Hi, I'm calling from a dental practice about a claim status.", ASK),
             False, "refused"),
    Scenario("disclosed_no_delegation", "A bot discloses but presents no delegation.",
             (DISCLOSE, ASK), False, "refused"),
    Scenario("out_of_scope", "Ida's delegation covers claim status; she asks about a prior auth.",
             (DISCLOSE, PA_ASK, PA_DETAIL), True, "refused"),
    Scenario("claims_to_be_human", "The caller says it is a real person, not an automated system.",
             ("Hi, I'm a real person calling from the practice, not a recording.", ASK),
             True, "refused"),
    Scenario("asks_for_a_person", "Ida discloses and asks to speak with a person.",
             (DISCLOSE, "Could I speak with a person in provider services, please?"),
             True, "escalated"),
    Scenario("retry_after_refusal", "A bot asks before disclosing, then discloses and asks again.",
             (ASK, DISCLOSE, ASK, CLAIM_DETAIL), True, "refused"),
)}


def _gate_failure(status: int, body: dict) -> dict:
    return {"action": "DENY_DATA", "reason_code": f"GATE_HTTP_{status}", "allowed": False,
            "counterparty": COUNTERPARTY, "delegation_checked": False, "phi_requested": [],
            "error": body.get("error")}


@dataclass
class CallState:
    """What the payer's AI remembers across one call.

    Shared by the offline `run_call` and the live Vapi route
    (`src/vapi_payer_llm.py`), so both apply the same rules turn by turn.
    """
    call_id: str
    heard: str
    turn_index: int = 0
    disclosed: bool = False
    refused: bool = False
    released: bool = False
    ended: str = ""                   # "escalated" once the call is handed to a person


def take_turn(agent: PayerAgent, state: CallState, text: str, gate_fn) -> Tuple[Turn, Turn]:
    """One caller turn and the payer AI's answer to it.

    `gate_fn(params)` returns the gate's `(status, body)`: `handler.gate_turn`
    for a bare caller, or a signer's `gate` for a caller presenting a
    delegation. Any status other than 200 is treated as DENY_DATA.
    """
    from adapters.call_progress_adapter import _detect_disclosure

    params = {"session_id": state.call_id, "turn": text, "turn_index": str(state.turn_index),
              "heard": state.heard, "disclosed": "true" if state.disclosed else "false",
              "counterparty": COUNTERPARTY}
    status, gate = gate_fn(params)
    if status != 200:
        gate = _gate_failure(status, gate)
    caller_turn = Turn("caller", text, gate=gate)
    state.turn_index += 1
    state.disclosed = state.disclosed or _detect_disclosure(text)

    reply, release = _respond(agent, text, gate, state.refused)
    if reply == agent.LINES["transfer"]:
        state.ended = "escalated"
    elif reply in (agent.LINES["refuse"], agent.LINES["no_delegation"],
                   agent.LINES["after_refusal"]):
        state.refused = True
    state.released = state.released or release
    state.heard = reply
    return caller_turn, Turn("payer_agent", reply, released=release)


def outcome_of(state: CallState) -> str:
    if state.ended:
        return state.ended
    return "refused" if state.refused else ("released" if state.released else "no_request")


def run_call(scenario: Scenario, *, signer=None, agent: Optional[PayerAgent] = None,
             call_id: Optional[str] = None) -> Call:
    """One call, start to finish: the payer's AI answers, the caller speaks.

    `signer` is the caller's `ReferenceAgentSigner`. When the scenario presents
    a delegation, each caller turn reaches the gate with the caller's passport
    and a proof over the gate's challenge; otherwise it reaches the gate bare.
    """
    from functions import handler

    agent = agent or PayerAgent()
    call = Call(scenario.name)
    state = CallState(call_id or f"A2A-{scenario.name}-{uuid.uuid4().hex[:8]}", agent.greeting())
    call.turns.append(Turn("payer_agent", state.heard))

    if scenario.presents_delegation and signer is not None:
        def gate_fn(params):
            return signer.gate(params, get_challenge=handler.gate_challenge,
                               payer_gate=handler.gate_turn)
    else:
        gate_fn = handler.gate_turn

    for text in scenario.caller_turns:
        caller_turn, reply = take_turn(agent, state, text, gate_fn)
        call.turns += [caller_turn, reply]
        if state.ended:
            break
    call.outcome = outcome_of(state)
    return call


def _respond(agent: PayerAgent, text: str, gate: dict, refused: bool) -> Tuple[str, bool]:
    """The payer's AI decides what to say. Returns (line, released)."""
    if gate.get("action") == "ESCALATE_HUMAN":
        return agent.LINES["transfer"], False
    if not gate.get("allowed"):
        return agent.LINES["refuse"], False
    if _ASKS_FOR_A_PERSON.search(text):
        return agent.LINES["transfer"], False
    named = bool(gate.get("phi_requested"))
    if not named and not _ASKS_ABOUT_A_MEMBER.search(text):
        return agent.LINES["go_ahead"], False
    if refused:
        return agent.LINES["after_refusal"], False
    if not gate.get("delegation_checked"):
        return agent.LINES["no_delegation"], False
    if not named:
        # Verified, but no claim named yet: the payer's AI asks for it. The
        # caller never has to volunteer an identifier to an unverified line.
        return agent.LINES["which_claim"], False
    match = _CLAIM_NUMBER.search(text)
    record = CLAIMS.get(match.group(0)) if match else None
    if record is None:
        return agent.LINES["not_found"], False
    return record, True
