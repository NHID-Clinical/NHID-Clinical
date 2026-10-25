"""
NHID-Clinical – Grok Realtime bridge
====================================
Holds the xAI Realtime WebSocket for a call the Grok agent places on behalf
of a provider, and puts the pre-utterance gate between the model and every
action it tries to take. The bridge enforces; the prompt is advisory.

What it does, in order
----------------------
1. ``session.update`` with the NHID tool (and any tools the deployment
   registers) so every function call surfaces to this process.
2. Speaks the disclosure itself with ``force_message`` (``interruptible:
   false``) before the model says anything. Disclosure is not left to the
   model.
3. For every ``response.function_call_arguments.done``, including transfer
   and end-call tools, calls ``functions.handler.gate_turn`` in process with a
   hard deadline BEFORE anything is executed:

     DENY_DATA          tool blocked; bridge speaks ``say_instead``
     DISCLOSE_IDENTITY  tool blocked; bridge speaks the disclosure again
     ESCALATE_HUMAN     tool blocked; the BRIDGE transfers (``refer``) and
                        records honored / not_honored; a failed transfer ends
                        the call
     CONTINUE_AI /      tool executed (if the deployment registered an
     LOG_ONLY           executor) and the result returned to the model

4. Fails closed. Any exception, timeout, non-200, missing or unknown action
   from the gate is DENY_DATA. Three consecutive gate failures end the call.
5. Checks speech after the fact: when a model turn's transcript completes, it
   is run through the gate and logged. Speech already streamed cannot be
   recalled; a DENY here is a recorded finding plus a corrective disclosure,
   not a prevention. The docs are explicit that a tool invoked during a voice
   response arrives after the audio.
6. Writes one JSONL audit line per decision: ids, action, reason code,
   violated rule ids, policy version, evidence hash when ATR-01 signed one,
   latency, and what the bridge did. No transcript text. PHI as field names
   only.

What it is not
--------------
Not the policy engine (``src/nhid_policy_engine_v1.py`` decides; this relays).
Not a certification, not production infrastructure, not deployed anywhere.
Not evidence of authority: the agent id is logged as ``actor_id`` and nothing
more. DLG-01 stays opt-in and is not wired here.

Transport and call control are injected, so the relay loop is tested with
fakes and the real WebSocket client is used only by ``main()``. The
``websockets`` package is imported there and nowhere else; it is not a
repository dependency.

Unverified (2026-10-25): the exact contracts of the SIP call-control routes
(``/v1/realtime/calls/{id}/refer`` and ``/hangup``) and whether a
console-published agent's built-in tools surface to a WebSocket client at
all. ``HttpCallControl`` implements the documented URL shape and says so.

NHID-Clinical is a voluntary open proposal. Apache-2.0 code. Not an
accredited standard, not a certification, not a regulatory requirement.
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional, Protocol

from adapters.grok_realtime_adapter import (  # noqa: E402
    END_CALL_TOOL_NAMES,
    classify_completed_turn,
    NHID_EVALUATE_TURN_TOOL,
    TRANSFER_TOOL_NAMES,
    FunctionCall,
    GrokCallState,
    force_message,
    function_call_output,
    gate_params,
    ingest,
    parse_function_call,
    session_update,
)

#: Actions the gate may return. Anything else is treated as DENY_DATA.
KNOWN_ACTIONS = frozenset({"DENY_DATA", "ESCALATE_HUMAN", "DISCLOSE_IDENTITY", "LOG_ONLY", "CONTINUE_AI"})
ALLOWING_ACTIONS = frozenset({"CONTINUE_AI", "LOG_ONLY"})

#: Reason code the bridge records when the gate did not answer. Not an engine
#: code: it names the bridge's own failure to obtain a decision.
GATE_UNAVAILABLE = "GATE_UNAVAILABLE"

DEFAULT_GATE_DEADLINE_S = 0.3
DEFAULT_MAX_GATE_FAILURES = 3


class Transport(Protocol):
    async def send(self, message: dict[str, Any]) -> None: ...
    async def recv(self) -> Optional[dict[str, Any]]: ...


class CallControl(Protocol):
    async def refer(self, call_id: str) -> bool: ...
    async def hangup(self, call_id: str) -> None: ...


GateFn = Callable[[dict[str, Any]], tuple[int, dict[str, Any]]]
Executor = Callable[[FunctionCall], Awaitable[dict[str, Any]]]


@dataclass
class Verdict:
    """What the bridge decided for one action, after the fail-closed rule."""
    allowed: bool
    action: str
    reason_code: str
    say_instead: Optional[str]
    instruction: str
    violations: list[str]
    policy_version: Optional[str]
    evidence_hash: Optional[str]
    gate_status: Optional[int]
    latency_ms: float
    gate_failed: bool = False


def _disclosure_text() -> str:
    from functions.demo_scripts import COMPLIANT_SCRIPT
    return COMPLIANT_SCRIPT[0]["text"]


def in_process_gate(params: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    """The gate the route runs, called without HTTP."""
    from functions.handler import gate_turn
    return gate_turn(params)


class NoCallControl:
    """For connections that are not phone calls (the ``?agent_id=`` form):
    there is nothing to transfer, so an escalation cannot be honored and is
    recorded as such."""
    async def refer(self, call_id: str) -> bool:
        return False

    async def hangup(self, call_id: str) -> None:
        return None


class HttpCallControl:
    """SIP call control over the documented URL shape. UNVERIFIED against a
    live call as of 2026-10-25: the paths came from the SIP section of the
    docs and have not been exercised. Treat a failure here as not_honored,
    which is what the bridge does."""

    def __init__(self, api_key: str, base_url: str = "https://api.x.ai/v1/realtime/calls",
                 timeout_s: float = 5.0):
        self._key = api_key
        self._base = base_url.rstrip("/")
        self._timeout = timeout_s

    async def _post(self, call_id: str, verb: str, body: Optional[dict[str, Any]] = None) -> bool:
        import httpx

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._base}/{call_id}/{verb}",
                headers={"Authorization": f"Bearer {self._key}"},
                json=body or {},
            )
            return 200 <= response.status_code < 300

    async def refer(self, call_id: str) -> bool:
        target = os.environ.get("NHID_TRANSFER_TARGET", "").strip()
        if not target:
            return False
        try:
            return await self._post(call_id, "refer", {"target_uri": target})
        except Exception:  # noqa: BLE001
            return False

    async def hangup(self, call_id: str) -> None:
        try:
            await self._post(call_id, "hangup")
        except Exception:  # noqa: BLE001
            return None


class Bridge:
    def __init__(
        self,
        transport: Transport,
        *,
        session_id: str,
        actor_id: str,
        call_control: Optional[CallControl] = None,
        gate: GateFn = in_process_gate,
        executors: Optional[dict[str, Executor]] = None,
        audit_path: Optional[Path] = None,
        instructions: Optional[str] = None,
        voice: Optional[str] = None,
        disclosure_text: Optional[str] = None,
        gate_deadline_s: float = DEFAULT_GATE_DEADLINE_S,
        max_gate_failures: int = DEFAULT_MAX_GATE_FAILURES,
        extra_tools: Optional[list[dict[str, Any]]] = None,
    ) -> None:
        self.transport = transport
        self.state = GrokCallState(session_id=session_id, actor_id=actor_id)
        self.call_control: CallControl = call_control or NoCallControl()
        self.gate = gate
        self.executors = dict(executors or {})
        self.audit_path = audit_path
        self.instructions = instructions
        self.voice = voice
        self.disclosure_text = disclosure_text or _disclosure_text()
        self.state.disclosure_text = self.disclosure_text
        self.gate_deadline_s = gate_deadline_s
        self.max_gate_failures = max_gate_failures
        self.extra_tools = list(extra_tools or [])
        self.sent: list[dict[str, Any]] = []       # every message sent, for tests and debugging
        self.audit_rows: list[dict[str, Any]] = []  # every audit row, mirrored to audit_path

    # ── lifecycle ────────────────────────────────────────────────────────────

    async def start(self) -> None:
        tools = [NHID_EVALUATE_TURN_TOOL] + self.extra_tools
        await self._send(session_update(self.instructions, tools, self.voice))
        await self._speak_disclosure()

    async def run(self) -> None:
        await self.start()
        while not self.state.ended:
            event = await self.transport.recv()
            if event is None:
                break
            await self.handle(event)

    async def handle(self, event: dict[str, Any]) -> None:
        kind = str(event.get("type") or "")
        transcript = str(event.get("transcript") or "")
        turn_kind = classify_completed_turn(self.state, transcript) \
            if kind == "response.output_audio_transcript.done" else None
        was_interrupted = self.state.disclosure_interrupted
        ingest(self.state, event)

        if turn_kind is not None:
            if turn_kind == "disclosure" and not was_interrupted:
                return                                   # credited; nothing to check
            if turn_kind in ("disclosure", "truncated"):
                await self._speak_disclosure()           # not credited: say it again
                return
            await self._check_spoken(transcript)         # the model's own turn
            return

        call = parse_function_call(event)
        if call is not None:
            await self._handle_call(call)

    # ── the gate ─────────────────────────────────────────────────────────────

    async def _consult_gate(self, planned_text: str) -> Verdict:
        """Run the gate under a deadline and apply the fail-closed rule."""
        params = gate_params(self.state, planned_text)
        started = time.perf_counter()
        status: Optional[int] = None
        body: dict[str, Any] = {}
        failed = False
        try:
            status, body = await asyncio.wait_for(
                asyncio.to_thread(self.gate, params), timeout=self.gate_deadline_s)
            if not isinstance(body, dict):
                failed = True
        except Exception:  # noqa: BLE001 - timeout, raise, anything: closed
            failed = True
        latency = (time.perf_counter() - started) * 1000.0

        action = str(body.get("action") or "") if not failed else ""
        if failed or status != 200 or action not in KNOWN_ACTIONS or "allowed" not in body:
            self.state.consecutive_gate_failures += 1
            return Verdict(
                allowed=False, action="DENY_DATA", reason_code=GATE_UNAVAILABLE,
                say_instead=self.disclosure_text,
                instruction="The gate did not return a decision; nothing proceeds.",
                violations=[], policy_version=None, evidence_hash=None,
                gate_status=status, latency_ms=latency, gate_failed=True,
            )
        self.state.consecutive_gate_failures = 0
        return Verdict(
            allowed=bool(body.get("allowed")) and action in ALLOWING_ACTIONS,
            action=action,
            reason_code=str(body.get("reason_code") or ""),
            say_instead=body.get("say_instead"),
            instruction=str(body.get("instruction") or ""),
            violations=sorted({v.get("rule_id", "") for v in body.get("violations") or [] if isinstance(v, dict)}),
            policy_version=body.get("policy_version"),
            evidence_hash=body.get("evidence_hash"),
            gate_status=status, latency_ms=latency,
        )

    # ── enforcement ──────────────────────────────────────────────────────────

    async def _handle_call(self, call: FunctionCall) -> None:
        verdict = await self._consult_gate(call.planned_utterance)
        enforcement = "executed"

        if verdict.action == "ESCALATE_HUMAN" or (verdict.allowed and call.intent == "transfer"):
            enforcement = await self._escalate(call)
        elif not verdict.allowed:
            enforcement = "blocked"
            await self._send(function_call_output(call.call_id, {
                "status": "blocked",
                "allowed": False,
                "action": verdict.action,
                "reason_code": verdict.reason_code,
                "instruction": verdict.instruction,
                "say_instead": verdict.say_instead,
            }))
            if verdict.action == "DISCLOSE_IDENTITY" or verdict.gate_failed:
                await self._speak_disclosure()
            elif verdict.say_instead:
                await self._send(force_message(verdict.say_instead))
        elif call.name in END_CALL_TOOL_NAMES or call.intent == "end_call":
            enforcement = "ended"
            await self._send(function_call_output(call.call_id, {"status": "ended", "allowed": True}))
            await self._end_call()
        else:
            output: dict[str, Any] = {
                "allowed": True, "action": verdict.action, "reason_code": verdict.reason_code,
                "instruction": verdict.instruction,
            }
            executor = self.executors.get(call.name)
            if executor is not None:
                try:
                    output["result"] = await executor(call)
                except Exception as exc:  # noqa: BLE001
                    output["result"] = {"error": f"{type(exc).__name__}"}
                    enforcement = "executor_error"
            await self._send(function_call_output(call.call_id, output))
            await self._send({"type": "response.create"})

        self._audit(event_type="function_call", tool=call.name, intent=call.intent,
                    verdict=verdict, enforcement=enforcement)
        self.state.pending_calls.pop(call.call_id, None)

        if self.state.consecutive_gate_failures >= self.max_gate_failures and not self.state.ended:
            self._audit(event_type="gate_unavailable_limit", tool=None, intent=None,
                        verdict=verdict, enforcement="ended")
            await self._end_call()

    async def _escalate(self, call: FunctionCall) -> str:
        """The bridge transfers; the model never does. The result goes into
        state so the next gate call carries it, which is how a failed transfer
        becomes a CRITICAL EIT-01 finding rather than an unknown outcome."""
        self.state.escalation_requested_turn = self.state.turn_index
        honored = await self.call_control.refer(self.state.session_id)
        self.state.escalation_outcome = "honored" if honored else "not_honored"
        await self._send(function_call_output(call.call_id, {
            "status": "transferring" if honored else "transfer_failed",
            "allowed": False,
            "action": "ESCALATE_HUMAN",
            "escalation_outcome": self.state.escalation_outcome,
        }))
        if honored:
            return "transferred"
        # A request for a human that cannot be honored must not become a
        # continued data exchange. Record it with the engine, then end.
        self._record_failed_escalation()
        await self._end_call()
        return "transfer_failed_call_ended"

    def _record_failed_escalation(self) -> None:
        """One synchronous gate call carrying escalation_outcome=not_honored, so
        the engine's own EIT-01 verdict is on the record for this call."""
        params = gate_params(self.state, "The transfer could not be completed.")
        started = time.perf_counter()
        try:
            status, body = self.gate(params)
        except Exception:  # noqa: BLE001
            status, body = None, {}
        latency = (time.perf_counter() - started) * 1000.0
        verdict = Verdict(
            allowed=False, action=str(body.get("action") or "DENY_DATA"),
            reason_code=str(body.get("reason_code") or GATE_UNAVAILABLE), say_instead=None,
            instruction="", violations=sorted({v.get("rule_id", "") for v in body.get("violations") or []
                                               if isinstance(v, dict)}),
            policy_version=body.get("policy_version"), evidence_hash=body.get("evidence_hash"),
            gate_status=status, latency_ms=latency, gate_failed=status != 200,
        )
        self._audit(event_type="escalation_outcome", tool=None, intent="transfer",
                    verdict=verdict, enforcement="recorded_not_honored")

    async def _check_spoken(self, transcript: str) -> None:
        """After-the-fact check of a model turn. Detection and record only."""
        text = transcript.strip()
        if not text:
            return
        verdict = await self._consult_gate(text)
        enforcement = "spoken_ok"
        if not verdict.allowed and not verdict.gate_failed:
            enforcement = "spoken_after_the_fact"
            if verdict.action in ("DENY_DATA", "DISCLOSE_IDENTITY") and verdict.say_instead:
                # Cannot recall speech. The corrective disclosure is spoken so the
                # representative hears it before any further exchange.
                await self._speak_disclosure()
        self._audit(event_type="spoken_turn", tool=None, intent="spoken",
                    verdict=verdict, enforcement=enforcement)

    # ── helpers ──────────────────────────────────────────────────────────────

    async def _speak_disclosure(self) -> None:
        self.state.pending_disclosure = True
        self.state.disclosure_interrupted = False
        await self._send(force_message(self.disclosure_text, interruptible=False))

    async def _end_call(self) -> None:
        self.state.ended = True
        await self.call_control.hangup(self.state.session_id)

    async def _send(self, message: dict[str, Any]) -> None:
        self.sent.append(message)
        await self.transport.send(message)

    def _audit(self, *, event_type: str, tool: Optional[str], intent: Optional[str],
               verdict: Verdict, enforcement: str) -> None:
        row = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "session_id": self.state.session_id,
            "actor_id": self.state.actor_id,
            "turn_index": self.state.turn_index,
            "event_type": event_type,
            "tool": tool,
            "intent": intent,
            "disclosed": self.state.disclosed,
            "action": verdict.action,
            "reason_code": verdict.reason_code,
            "violations": verdict.violations,
            "policy_version": verdict.policy_version,
            "evidence_hash": verdict.evidence_hash,
            "gate_status": verdict.gate_status,
            "gate_failed": verdict.gate_failed,
            "latency_ms": round(verdict.latency_ms, 1),
            "enforcement": enforcement,
        }
        self.audit_rows.append(row)
        if self.audit_path is not None:
            try:
                self.audit_path.parent.mkdir(parents=True, exist_ok=True)
                with self.audit_path.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps(row, sort_keys=True) + "\n")
            except OSError:
                pass


# ── the real WebSocket, used by main() only ─────────────────────────────────

class WebSocketTransport:
    """Thin wrapper over ``websockets``. Binary frames (audio) are dropped:
    this runner is a transcript-and-tools client for proving the gate, not a
    media path. ``websockets`` is imported here so the module above stays
    dependency-free."""

    def __init__(self, ws) -> None:
        self._ws = ws

    async def send(self, message: dict[str, Any]) -> None:
        await self._ws.send(json.dumps(message))

    async def recv(self) -> Optional[dict[str, Any]]:
        while True:
            try:
                raw = await self._ws.recv()
            except Exception:  # noqa: BLE001 - closed
                return None
            if isinstance(raw, (bytes, bytearray)):
                continue
            try:
                event = json.loads(raw)
            except ValueError:
                continue
            if isinstance(event, dict):
                return event


async def _main_async(args) -> int:
    try:
        import websockets  # type: ignore[import-not-found]
    except ImportError:
        print("the runner needs the `websockets` package: pip install websockets "
              "(it is deliberately not a repository dependency)")
        return 2
    key = os.environ.get("XAI_API_KEY", "").strip()
    if not key:
        print("XAI_API_KEY is not set")
        return 2
    if args.call_id:
        url = f"{args.url}?call_id={args.call_id}"
        control: CallControl = HttpCallControl(key)
        session_id = args.call_id
    else:
        url = f"{args.url}?agent_id={args.agent_id}" if args.agent_id else f"{args.url}?model={args.model}"
        control = NoCallControl()
        session_id = args.session_id or f"grok-{int(time.time())}"
    async with websockets.connect(url, additional_headers={"Authorization": f"Bearer {key}"}) as ws:
        bridge = Bridge(
            WebSocketTransport(ws), session_id=session_id,
            actor_id=args.actor_id or (args.agent_id or "grok-agent"),
            call_control=control, audit_path=Path(args.audit),
            instructions=args.instructions, voice=args.voice,
        )
        print(f"connected; audit -> {args.audit}; the key is never printed")
        await bridge.run()
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="python -m src.grok_realtime_bridge",
        description="Hold the xAI Realtime socket and gate every tool call through NHID-Clinical.",
    )
    parser.add_argument("--url", default="wss://api.x.ai/v1/realtime")
    parser.add_argument("--agent-id", help="a console-published agent (connection form taken from the console)")
    parser.add_argument("--call-id", help="a SIP call id from the realtime.call.incoming webhook")
    parser.add_argument("--model", default="grok-voice-latest")
    parser.add_argument("--session-id")
    parser.add_argument("--actor-id")
    parser.add_argument("--voice")
    parser.add_argument("--instructions")
    parser.add_argument("--audit", default="logs/grok_bridge_audit.jsonl")
    args = parser.parse_args(argv)
    return asyncio.run(_main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
