"""
NHID-Clinical – Grok Realtime adapter
=====================================
Pure mapping between xAI Realtime WebSocket events and the parameters of the
pre-utterance gate (``functions.handler.gate_turn``). No I/O, no detection:
every judgement about the words stays in the engine, reached through the
gate. This module only remembers what has happened on the call and shapes
one gate request from it.

Orientation (the canonical scenario, docs/canonical-threat-model.md): the
Grok agent is the CALLER, acting for a provider; the party on the other end
is the payer's representative. The caller transcript is what the
representative said; the agent's planned utterance or tool call is what the
gate judges.

Events read (names verified against docs.x.ai, speech-to-speech, 2026-10-25):

  conversation.item.input_audio_transcription.completed   the representative's words (final)
  conversation.item.input_audio_transcription.updated     cumulative transcript (xAI extension)
  response.output_audio_transcript.done                   the agent finished a spoken turn
  response.done                                           a response ended; status tells whether it completed
  response.function_call_arguments.done                   the model wants a tool run: {name, call_id, arguments}
  input_audio_buffer.speech_started                       the representative started talking (barge-in)

Timing fact that shapes the bridge: when the model invokes a tool during a
voice response, the audio deltas arrive first and the function-call event
arrives alongside ``response.done``. A tool call can therefore gate what the
agent DOES next, never what it has already SAID. Disclosure is made
deterministic with a ``force_message`` the bridge sends itself; speech is
checked after the fact and logged.

Two things this module never does: it never trusts the model's claim about
whether disclosure happened (``disclosed`` is set only from the bridge's own
observation of a completed disclosure turn), and it never decides anything.

NHID-Clinical is a voluntary open proposal. Apache-2.0 code; the controls it
reaches are CC BY 4.0 text. Not an accredited standard, not a certification.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

#: The one tool the model is given to ask permission. The bridge gates every
#: function call regardless of whether the model used it; the tool exists so
#: a well-behaved model can ask before speaking, and so the "intent" of a
#: planned turn is on the record.
NHID_EVALUATE_TURN_TOOL: dict[str, Any] = {
    "type": "function",
    "name": "nhid_evaluate_turn",
    "description": (
        "Call BEFORE asking for, stating, or acting on any member, patient, claim "
        "or provider identifier, and before any transfer. Returns whether you may "
        "proceed and what to say instead."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "planned_utterance": {
                "type": "string",
                "maxLength": 4000,
                "description": "Exactly what you are about to say.",
            },
            "intent": {
                "type": "string",
                "enum": ["request_data", "disclose_data", "transfer", "end_call", "other"],
            },
        },
        "required": ["planned_utterance", "intent"],
        "additionalProperties": False,
    },
}

#: Console-built tool names the bridge treats as call control. They are gated
#: like any other call and then executed by the bridge, never by the model.
TRANSFER_TOOL_NAMES = frozenset({"transfer_call", "transfer", "escalate_to_human"})
END_CALL_TOOL_NAMES = frozenset({"end_call", "hangup", "hang_up"})


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class FunctionCall:
    name: str
    call_id: str
    arguments: dict[str, Any]
    raw_arguments: str

    @property
    def planned_utterance(self) -> str:
        """The text the gate judges. For the NHID tool it is the model's own
        planned words; for any other tool it is the tool name plus its
        arguments, so a data lookup carrying a member ID is seen for what it
        is."""
        text = str(self.arguments.get("planned_utterance") or "").strip()
        if text:
            return text
        return f"[{self.name}] {self.raw_arguments}".strip()

    @property
    def intent(self) -> str:
        declared = str(self.arguments.get("intent") or "").strip()
        if declared:
            return declared
        if self.name in TRANSFER_TOOL_NAMES:
            return "transfer"
        if self.name in END_CALL_TOOL_NAMES:
            return "end_call"
        return "tool"


@dataclass
class GrokCallState:
    """Everything the bridge knows about one call. The bridge, not the model,
    owns every field here."""
    session_id: str
    actor_id: str
    turn_index: int = 0
    disclosed: bool = False
    disclosed_at: Optional[str] = None
    last_heard: str = ""
    #: A disclosure force_message was sent and its spoken turn has not yet
    #: completed. Set by the bridge when it sends the disclosure.
    pending_disclosure: bool = False
    #: The representative started talking while a pending disclosure was
    #: playing. With interruptible=false this should not happen, but the
    #: engine's rule is that a disclosure counts only if it was heard, so the
    #: adapter records it rather than assuming.
    disclosure_interrupted: bool = False
    escalation_requested_turn: Optional[int] = None
    #: The engine's own vocabulary ("honored" / "not_honored"), reported on the
    #: next gate call so a failed transfer is a CRITICAL EIT-01 finding.
    escalation_outcome: Optional[str] = None
    consecutive_gate_failures: int = 0
    ended: bool = False
    events_seen: int = 0
    pending_calls: dict[str, FunctionCall] = field(default_factory=dict)
    #: The disclosure the bridge speaks. A completed turn is credited as the
    #: disclosure only when its transcript is that text; any other completed
    #: turn is the model talking, whatever the bridge was waiting for.
    disclosure_text: str = ""


_NORM_RE = re.compile(r"[^a-z0-9 ]+")


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", _NORM_RE.sub(" ", text.lower())).strip()


def classify_completed_turn(state: GrokCallState, transcript: str) -> str:
    """What a ``response.output_audio_transcript.done`` was.

    ``"disclosure"``  the pending disclosure, spoken through (at least the
                      first 60% of it, so a trailing clip does not void it)
    ``"truncated"``   a prefix of the disclosure shorter than that: cut off,
                      not credited, to be repeated
    ``"model"``       anything else: the model's own turn
    """
    if not state.pending_disclosure or not state.disclosure_text:
        return "model"
    full = _norm(state.disclosure_text)
    said = _norm(transcript)
    if not said:
        return "truncated"
    head = full[: max(1, int(len(full) * 0.6))]
    if said.startswith(head):
        return "disclosure"
    if full.startswith(said):
        return "truncated"
    return "model"


def parse_function_call(event: dict[str, Any]) -> Optional[FunctionCall]:
    """``response.function_call_arguments.done`` → FunctionCall, or None.

    Arguments arrive as a JSON string. A string that is not JSON is kept as
    the raw text so the gate still sees it; the model's formatting error must
    not become an unguarded tool call."""
    if event.get("type") != "response.function_call_arguments.done":
        return None
    raw = event.get("arguments")
    raw_text = raw if isinstance(raw, str) else json.dumps(raw or {})
    try:
        parsed = json.loads(raw_text) if raw_text.strip() else {}
    except (TypeError, ValueError):
        parsed = {}
    if not isinstance(parsed, dict):
        parsed = {}
    return FunctionCall(
        name=str(event.get("name") or "").strip() or "unnamed_tool",
        call_id=str(event.get("call_id") or "").strip(),
        arguments=parsed,
        raw_arguments=raw_text,
    )


def ingest(state: GrokCallState, event: dict[str, Any]) -> GrokCallState:
    """Fold one server event into the call state. Returns the same object.

    Only state changes here; nothing is judged. The disclosure flag moves
    from pending to established only when the disclosure's spoken turn
    completes without the representative talking over it, which is the
    adapter-level reading of "a disclosure counts only if it was heard"
    (docs/CONTROL_DECISION_TABLE.md, IDG-01).
    """
    state.events_seen += 1
    kind = str(event.get("type") or "")

    if kind in ("conversation.item.input_audio_transcription.completed",
                "conversation.item.input_audio_transcription.updated"):
        text = str(event.get("transcript") or "").strip()
        if text:
            state.last_heard = text

    elif kind == "input_audio_buffer.speech_started":
        if state.pending_disclosure:
            state.disclosure_interrupted = True

    elif kind == "response.output_audio_transcript.done":
        state.turn_index += 1
        kind_of_turn = classify_completed_turn(state, str(event.get("transcript") or ""))
        if kind_of_turn == "disclosure":
            if state.disclosure_interrupted:
                # Spoken through but talked over: not credited. Said again.
                state.pending_disclosure = False
                state.disclosure_interrupted = False
            else:
                state.disclosed = True
                state.disclosed_at = _now_iso()
                state.pending_disclosure = False
        elif kind_of_turn == "truncated":
            state.pending_disclosure = False
            state.disclosure_interrupted = False
        # "model": the model spoke while a disclosure was still owed; the
        # pending flag stays so the bridge keeps waiting for the real one.

    elif kind == "response.done":
        response = event.get("response") or {}
        status = str(response.get("status") or "").lower()
        if state.pending_disclosure and status in ("cancelled", "canceled", "incomplete", "failed"):
            state.pending_disclosure = False
            state.disclosure_interrupted = False

    call = parse_function_call(event)
    if call is not None and call.call_id:
        state.pending_calls[call.call_id] = call

    return state


def gate_params(state: GrokCallState, planned_text: str) -> dict[str, Any]:
    """The gate request for one planned action. Every field comes from the
    bridge's state; the model's arguments supply only the planned words."""
    params: dict[str, Any] = {
        "session_id": state.session_id,
        "turn": planned_text,
        "disclosed": "true" if state.disclosed else "false",
        "turn_index": state.turn_index,
        "heard": state.last_heard,
        "actor_id": state.actor_id,
    }
    if state.disclosed and state.disclosed_at:
        params["disclosed_at"] = state.disclosed_at
    if state.escalation_outcome:
        params["escalation_outcome"] = state.escalation_outcome
    return params


def force_message(text: str, *, interruptible: bool = False) -> dict[str, Any]:
    """A scripted utterance the server synthesises without the model. The
    bridge uses it for the disclosure and for ``say_instead``. Per the docs,
    no ``response.create`` follows: the force_message is the turn."""
    return {
        "type": "conversation.item.create",
        "item": {
            "type": "force_message",
            "role": "assistant",
            "interruptible": interruptible,
            "content": [{"type": "output_text", "text": text}],
        },
    }


def function_call_output(call_id: str, output: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "conversation.item.create",
        "item": {
            "type": "function_call_output",
            "call_id": call_id,
            "output": json.dumps(output, sort_keys=True),
        },
    }


def session_update(instructions: Optional[str], tools: list[dict[str, Any]],
                   voice: Optional[str] = None) -> dict[str, Any]:
    session: dict[str, Any] = {"tools": tools, "turn_detection": {"type": "server_vad"}}
    if instructions:
        session["instructions"] = instructions
    if voice:
        session["voice"] = voice
    return {"type": "session.update", "session": session}
