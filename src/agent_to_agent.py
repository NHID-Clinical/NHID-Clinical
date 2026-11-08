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
_ASKS_FOR_A_PERSON = re.compile(
    r"\b(speak|talk)\s+(to|with)\s+(a|an|someone|somebody)\s*"
    r"(person|human|representative|someone)?", re.IGNORECASE)


@dataclass
class PayerAgent:
    """The payer's reference AI agent, answering the provider line."""
    payer: str = "Acme Health"

    LINES = {
        "go_ahead": "Go ahead.",
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


DISCLOSE = ("Hi, this is Ida, an automated AI assistant calling for a demonstration dental "
            "practice about a claim status.")
ASK = "The member ID is RVD-204-7731 and the claim number is 9921-0417. What's the status?"

SCENARIOS: Dict[str, Scenario] = {s.name: s for s in (
    Scenario("verified_ida", "Ida discloses, presents a verified delegation, asks for one claim.",
             (DISCLOSE, ASK), True, "released"),
    Scenario("undisclosed_bot", "A bot never says it is automated and asks for a claim.",
             ("Hi, I'm calling from a dental practice about a claim status.", ASK),
             False, "refused"),
    Scenario("disclosed_no_delegation", "A bot discloses but presents no delegation.",
             (DISCLOSE, ASK), False, "refused"),
    Scenario("out_of_scope", "Ida's delegation covers claim status; she asks for a prior auth.",
             (DISCLOSE, "The member ID is RVD-204-7731. What's the status of prior auth "
                        "number PA-55120934?"), True, "refused"),
    Scenario("claims_to_be_human", "The caller says it is a real person, not an automated system.",
             ("Hi, I'm a real person calling from the practice, not a recording.", ASK),
             True, "refused"),
    Scenario("asks_for_a_person", "Ida discloses and asks to speak with a person.",
             (DISCLOSE, "Could I speak with a person in provider services, please?"),
             True, "escalated"),
    Scenario("retry_after_refusal", "A bot asks before disclosing, then discloses and asks again.",
             (ASK, DISCLOSE, ASK), True, "refused"),
)}


def _gate_failure(status: int, body: dict) -> dict:
    return {"action": "DENY_DATA", "reason_code": f"GATE_HTTP_{status}", "allowed": False,
            "counterparty": COUNTERPARTY, "delegation_checked": False, "phi_requested": [],
            "error": body.get("error")}


def run_call(scenario: Scenario, *, signer=None, agent: Optional[PayerAgent] = None,
             call_id: Optional[str] = None) -> Call:
    """One call, start to finish: the payer's AI answers, the caller speaks.

    `signer` is the caller's `ReferenceAgentSigner`. When the scenario presents
    a delegation, each caller turn reaches the gate with the caller's passport
    and a proof over the gate's challenge; otherwise it reaches the gate bare.
    """
    from adapters.call_progress_adapter import _detect_disclosure
    from functions import handler

    agent = agent or PayerAgent()
    call_id = call_id or f"A2A-{scenario.name}-{uuid.uuid4().hex[:8]}"
    call = Call(scenario.name)
    heard = agent.greeting()
    call.turns.append(Turn("payer_agent", heard))
    disclosed = refused = released = False

    for index, text in enumerate(scenario.caller_turns):
        params = {"session_id": call_id, "turn": text, "turn_index": str(index),
                  "heard": heard, "disclosed": "true" if disclosed else "false",
                  "counterparty": COUNTERPARTY}
        if scenario.presents_delegation and signer is not None:
            status, gate = signer.gate(params, get_challenge=handler.gate_challenge,
                                       payer_gate=handler.gate_turn)
        else:
            status, gate = handler.gate_turn(params)
        if status != 200:
            gate = _gate_failure(status, gate)
        call.turns.append(Turn("caller", text, gate=gate))
        disclosed = disclosed or _detect_disclosure(text)

        reply, release = _respond(agent, text, gate, refused)
        if reply == agent.LINES["transfer"]:
            call.turns.append(Turn("payer_agent", reply))
            call.outcome = "escalated"
            return call
        if reply in (agent.LINES["refuse"], agent.LINES["no_delegation"],
                     agent.LINES["after_refusal"]):
            refused = True
        released = released or release
        call.turns.append(Turn("payer_agent", reply, released=release))
        heard = reply

    call.outcome = "refused" if refused else ("released" if released else "no_request")
    return call


def _respond(agent: PayerAgent, text: str, gate: dict, refused: bool) -> Tuple[str, bool]:
    """The payer's AI decides what to say. Returns (line, released)."""
    if gate.get("action") == "ESCALATE_HUMAN":
        return agent.LINES["transfer"], False
    if not gate.get("allowed"):
        return agent.LINES["refuse"], False
    if _ASKS_FOR_A_PERSON.search(text):
        return agent.LINES["transfer"], False
    if not gate.get("phi_requested"):
        return agent.LINES["go_ahead"], False
    if refused:
        return agent.LINES["after_refusal"], False
    if not gate.get("delegation_checked"):
        return agent.LINES["no_delegation"], False
    match = _CLAIM_NUMBER.search(text)
    record = CLAIMS.get(match.group(0)) if match else None
    if record is None:
        return agent.LINES["not_found"], False
    return record, True
