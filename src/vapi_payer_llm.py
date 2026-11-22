"""The payer's AI on a live Vapi call: the NHID gate on every caller turn.

docs/agent-to-agent-calls.md. The canonical direction holds (CLAUDE.md §1): a
caller-agent telephones the payer and asks for a patient's claim status. Here
the payer's AI is a Vapi assistant whose "Custom LLM" is this module. Vapi
sends every turn to `POST /v1/vapi/payer-llm/chat/completions` in the OpenAI
chat-completions format; this module takes the caller's newest line, runs it
through the payer's gate (`functions.handler.gate_turn`, counterparty
`ai_agent`) and answers with the deterministic `PayerAgent` line.

So the words the payer's AI speaks never come from a free-running model. They
come from `agent_to_agent.take_turn`, the same code the offline `run_call`
uses, which is what lets a test pin the live behavior.

Who is judged: the CALLER. The payer's AI is the enforcement point, not a
subject of the controls.

What this is not: a payer deployment. Both ends of a test call are our own
agents on fictional data. Research stage; see docs/claim-boundaries.md.
"""
from __future__ import annotations

import hmac
import json
import os
import threading
import time
import uuid
from collections import OrderedDict
from typing import Iterator, Optional, Tuple

from src.agent_to_agent import CallState, PayerAgent, outcome_of, take_turn

MODEL_NAME = "nhid-payer-reference"
SECRET_ENV = "NHID_VAPI_SECRET"
MAX_CALLS = 1000          # calls remembered at once; the oldest is dropped first
MAX_TURN_CHARS = 2000     # one caller turn; longer is refused, not truncated


class CallBook:
    """Per-call state, keyed by Vapi's call id. Bounded, thread-safe."""

    def __init__(self, limit: int = MAX_CALLS):
        self._calls: "OrderedDict[str, CallState]" = OrderedDict()
        # call id -> (message count, caller line, gate answer) of the turn last answered
        self.last: dict = {}
        self._limit = limit
        self._lock = threading.Lock()

    def get(self, call_id: str, agent: PayerAgent) -> CallState:
        with self._lock:
            state = self._calls.get(call_id)
            if state is None:
                state = CallState(call_id, agent.greeting())
                self._calls[call_id] = state
                while len(self._calls) > self._limit:
                    dropped, _ = self._calls.popitem(last=False)
                    self.last.pop(dropped, None)
            else:
                self._calls.move_to_end(call_id)
            return state

    def lock(self):
        return self._lock


CALLS = CallBook()


def secret_status(headers) -> Tuple[int, str]:
    """(200, "") when the request carries the configured secret.

    Vapi sends the secret configured on the assistant's server or credential
    as `X-Vapi-Secret`, or as a bearer token for a Custom LLM credential; both
    are accepted. With no secret configured, strict deployments refuse (503)
    and development accepts, matching the Twilio webhook rule.
    """
    from src.webhook_security import STRICT_MODES, deployment_mode

    secret = (os.getenv(SECRET_ENV) or "").strip()
    if not secret:
        if deployment_mode() in STRICT_MODES:
            return 503, f"Vapi verification is not configured: {SECRET_ENV} is unset"
        return 200, ""
    presented = (headers.get("x-vapi-secret") or "").strip()
    if not presented:
        auth = (headers.get("authorization") or "").strip()
        if auth.lower().startswith("bearer "):
            presented = auth[7:].strip()
    if presented and hmac.compare_digest(presented.encode(), secret.encode()):
        return 200, ""
    return 401, "Missing or wrong Vapi secret"


def _call_id(body: dict) -> str:
    call = body.get("call") if isinstance(body.get("call"), dict) else {}
    return str(call.get("id") or body.get("call_id") or "").strip()


def _latest_caller_line(body: dict) -> Optional[str]:
    """The newest `user` message: on the payer's side, the caller speaks as user."""
    messages = body.get("messages")
    if not isinstance(messages, list):
        return None
    for message in reversed(messages):
        if isinstance(message, dict) and message.get("role") == "user":
            content = message.get("content")
            if isinstance(content, list):   # OpenAI content parts
                content = " ".join(p.get("text", "") for p in content if isinstance(p, dict))
            if isinstance(content, str) and content.strip():
                return content.strip()
    return None


def answer(body: dict, *, agent: Optional[PayerAgent] = None, book: Optional[CallBook] = None,
           gate_fn=None) -> Tuple[int, dict]:
    """Decide the payer AI's next line for one Vapi request.

    Returns (status, result). On 200, result has `text` (what to say),
    `outcome`, `gate` (the gate's answer for the caller's turn, or None) and
    `call_id`. A caller line that was already answered is not gated twice:
    Vapi can resend a turn, and the gate's state must not count it again.
    """
    from functions import handler

    agent = agent or PayerAgent()
    book = book if book is not None else CALLS
    gate_fn = gate_fn or handler.gate_turn
    if not isinstance(body, dict):
        return 400, {"error": "Request body must be a JSON object"}
    call_id = _call_id(body)
    if not call_id:
        return 400, {"error": "call.id is required"}
    if len(call_id) > 200:
        return 400, {"error": "call.id is longer than 200 characters"}

    line = _latest_caller_line(body)
    state = book.get(call_id, agent)
    if line is None:
        return 200, {"call_id": call_id, "text": state.heard, "outcome": outcome_of(state),
                     "gate": None}
    if len(line) > MAX_TURN_CHARS:
        return 400, {"error": f"caller turn is longer than {MAX_TURN_CHARS} characters"}

    with book.lock():
        key = (len(body.get("messages") or []), line)
        last = book.last.get(call_id)
        if last and last[:2] == key:
            return 200, {"call_id": call_id, "text": state.heard, "outcome": outcome_of(state),
                         "gate": last[2]}
        if state.ended:
            return 200, {"call_id": call_id, "text": agent.LINES["transfer"],
                         "outcome": outcome_of(state), "gate": None}
        caller_turn, reply = take_turn(agent, state, line, gate_fn)
        book.last[call_id] = (*key, caller_turn.gate)
    return 200, {"call_id": call_id, "text": reply.text, "outcome": outcome_of(state),
                 "gate": caller_turn.gate, "released": reply.released}


# ── OpenAI chat-completions wire format ────────────────────────────────────

def completion(text: str) -> dict:
    """A non-streamed chat completion carrying `text`."""
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:24]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": MODEL_NAME,
        "choices": [{"index": 0, "finish_reason": "stop",
                     "message": {"role": "assistant", "content": text}}],
    }


def stream(text: str) -> Iterator[str]:
    """The same answer as server-sent events, which Vapi asks for by default."""
    cid = f"chatcmpl-{uuid.uuid4().hex[:24]}"
    created = int(time.time())

    def chunk(delta: dict, finish: Optional[str]) -> str:
        return "data: " + json.dumps({
            "id": cid, "object": "chat.completion.chunk", "created": created,
            "model": MODEL_NAME,
            "choices": [{"index": 0, "delta": delta, "finish_reason": finish}],
        }) + "\n\n"

    yield chunk({"role": "assistant", "content": text}, None)
    yield chunk({}, "stop")
    yield "data: [DONE]\n\n"


# ── After the call: the caller's transcript as an NHID record ──────────────

def end_of_call_record(body: dict) -> Tuple[int, dict]:
    """Turn the caller assistant's `end-of-call-report` into an NHID trace.

    Other Vapi server messages are acknowledged and ignored. When
    `NHID_VAPI_EVIDENCE_DIR` is set, the trace is also written there as
    `<call id>.json`.
    """
    from adapters.vapi_adapter import vapi_to_nhid_trace

    message = body.get("message") if isinstance(body, dict) else None
    if not isinstance(message, dict):
        return 400, {"error": "Expected a Vapi server message: {\"message\": {...}}"}
    kind = message.get("type")
    if kind != "end-of-call-report":
        return 200, {"ignored": kind or "unknown"}
    call = message.get("call") if isinstance(message.get("call"), dict) else {}
    artifact = message.get("artifact") if isinstance(message.get("artifact"), dict) else {}
    messages = artifact.get("messages") or message.get("messages") or []
    if not isinstance(messages, list):
        return 400, {"error": "artifact.messages must be a list"}
    # Vapi includes the assistant's system prompt as a message; it was never spoken.
    spoken = [m for m in messages if isinstance(m, dict) and m.get("role") in ("bot", "user")]
    trace = vapi_to_nhid_trace({"call": call, "messages": spoken})

    out_dir = (os.getenv("NHID_VAPI_EVIDENCE_DIR") or "").strip()
    call_id = str(call.get("id") or "")
    if out_dir and call_id and all(c.isalnum() or c in "-_" for c in call_id):
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, f"{call_id}.json"), "w", encoding="utf-8") as f:
            json.dump({"vapi_messages": spoken, "nhid_trace": trace}, f, indent=2)
    return 200, {"call_id": call_id, "nhid_trace": trace}
