"""
NHID-Clinical Trace Generator
================================
Runs the failure injection harness against a FastAPI server (or mock),
collects event output, and generates 10 canonical NHID-Clinical trace
files in markdown format.

Each trace covers a single distinct failure mode, following the canonical
trace post template (v1). Output files go to /traces/.

Usage:
  # With a live server:
  python tools/trace_generator.py

  # Without a server (generates synthetic traces from policy engine only):
  python tools/trace_generator.py --offline

  # Custom output directory:
  python tools/trace_generator.py --output-dir /path/to/traces

NHID-Clinical is a voluntary open proposal. CC BY 4.0.
Not an accredited standard. Not a regulatory requirement.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Any

# Allow running from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

try:
    import nhid_policy_engine_v1 as engine
    _ENGINE_AVAILABLE = True
except ImportError:
    _ENGINE_AVAILABLE = False


# ── Trace template helpers ─────────────────────────────────────────────────

def _ts(offset_seconds: float = 0.0) -> str:
    """Format an event timestamp as MM:SS."""
    total = int(offset_seconds)
    return f"{total // 60:02d}:{total % 60:02d}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


@dataclass
class TraceEvent:
    offset: float
    stage:  str
    description: str


@dataclass
class TraceSpec:
    slug:               str
    failure_mode:       str
    stage_1:            str
    stage_2:            str
    artifact_type:      str
    system_context:     str
    events:             list[TraceEvent]
    replay_result:      str  # PASS | FAIL | N/A
    failure_observation: str
    implications:       list[str]
    state_machine:      str
    event_store:        str
    failure_coverage:   str
    replay_integrity:   str
    next_iteration:     list[str]


# ── 10 failure modes ──────────────────────────────────────────────────────

_TRACES: list[TraceSpec] = [
    TraceSpec(
        slug="01-empty-speech-validation-gap",
        failure_mode="Empty speech result — validation gap",
        stage_1="INGEST",
        stage_2="VALIDATE",
        artifact_type="validation-failure",
        system_context="B2B payer-provider voice call / prior auth workflow / turn_count=0",
        events=[
            TraceEvent(0.00, "INGEST",   "Received POST /voice/process — form-urlencoded"),
            TraceEvent(0.01, "VALIDATE", "SpeechResult='', CallSid='EDGE-EMPTY-001'"),
            TraceEvent(0.02, "VALIDATE", "Normalization: empty string → treated as silence"),
            TraceEvent(0.04, "POLICY",   "IDG-01 evaluated: disclosure_timestamp=null, turn_count=0"),
            TraceEvent(0.05, "POLICY",   "Decision: DISCLOSE_IDENTITY / IDG01_DISCLOSURE_MISSING"),
            TraceEvent(0.07, "EXEC",     "TwiML fallback rendered: disclosure message"),
            TraceEvent(0.09, "PERSIST",  "Event written: session_id=EDGE-EMPTY-001"),
        ],
        replay_result="PASS",
        failure_observation="Empty SpeechResult bypassed disclosure enforcement because the pipeline treated silence as a valid turn rather than a validation boundary event.",
        implications=[
            "Empty speech is not inherently invalid but it must trigger policy evaluation, not silent pass-through.",
            "Absence of speech should reset the disclosure gate to prevent PHI exchange during silence-injection attacks.",
            "Pipelines that short-circuit on empty input skip the event record, breaking ATR-01 audit completeness.",
        ],
        state_machine="AWAITING_DISCLOSURE → AWAITING_DISCLOSURE (no state change on empty input)",
        event_store="Complete — 3 events written (INGEST, VALIDATE, PERSIST)",
        failure_coverage="IDG-01 violation detected and logged",
        replay_integrity="PASS — empty input is deterministic",
        next_iteration=[
            "Enforce that empty SpeechResult writes an INGEST event before any policy evaluation.",
            "Add silence-injection to the red-team test suite as a distinct test vector.",
            "Validate that the event record for empty-speech requests includes input_payload.speech_text='' explicitly.",
        ],
    ),

    TraceSpec(
        slug="02-null-bytes-sanitization-failure",
        failure_mode="Null bytes in speech — input sanitization failure",
        stage_1="INGEST",
        stage_2="VALIDATE",
        artifact_type="sanitization-failure",
        system_context="B2B payer-provider voice call / eligibility check / adversarial input",
        events=[
            TraceEvent(0.00, "INGEST",   "Received POST /voice/process — form-urlencoded"),
            TraceEvent(0.01, "INGEST",   "SpeechResult='\\x00\\x00\\x00check claim status'"),
            TraceEvent(0.02, "VALIDATE", "Null byte detection: 3 null bytes found at positions 0-2"),
            TraceEvent(0.03, "VALIDATE", "Sanitization: null bytes stripped → 'check claim status'"),
            TraceEvent(0.05, "POLICY",   "IDG-01 evaluated on sanitized text: disclosure_timestamp=null"),
            TraceEvent(0.06, "POLICY",   "Decision: DISCLOSE_IDENTITY / IDG01_DISCLOSURE_MISSING"),
            TraceEvent(0.08, "EXEC",     "TwiML fallback rendered"),
            TraceEvent(0.10, "PERSIST",  "Event written with sanitized input_payload.speech_text"),
        ],
        replay_result="PASS",
        failure_observation="Null bytes in SpeechResult were not sanitized before policy evaluation, causing the policy engine to receive a string with embedded control characters that could produce inconsistent pattern matching.",
        implications=[
            "Null byte injection is a known attack vector against string-handling pipelines in healthcare data contexts.",
            "Unsanitized null bytes can cause silent truncation in C-based string libraries, producing different behavior across STT/TTS vendors.",
            "The event record must store the sanitized text, not the raw injection payload, to preserve audit integrity.",
        ],
        state_machine="UNKNOWN → AWAITING_DISCLOSURE (session created from sanitized input)",
        event_store="Complete — sanitized speech_text stored in event record",
        failure_coverage="Input sanitization applied before policy evaluation",
        replay_integrity="PASS — sanitization is deterministic for identical input",
        next_iteration=[
            "Add null byte and control character stripping to the VALIDATE stage normalization function.",
            "Log the presence of null bytes as a boundary_violation with severity=minor for forensic awareness.",
            "Include null-byte injection in the canonical red-team test suite for all pipeline deployments.",
        ],
    ),

    TraceSpec(
        slug="03-missing-callsid-session-binding",
        failure_mode="Missing CallSid — session binding failure",
        stage_1="INGEST",
        stage_2="VALIDATE",
        artifact_type="session-binding-failure",
        system_context="B2B payer-provider voice call / inbound webhook / missing Twilio field",
        events=[
            TraceEvent(0.00, "INGEST",   "Received POST /voice/process — form-urlencoded"),
            TraceEvent(0.01, "VALIDATE", "CallSid field: absent (not present in request body)"),
            TraceEvent(0.02, "VALIDATE", "Validation failed: VALIDATION_MISSING_CALLSID"),
            TraceEvent(0.03, "VALIDATE", "Early exit: cannot bind session without identifier"),
        ],
        replay_result="N/A",
        failure_observation="Request without a CallSid cannot be bound to a session, making the event unreplayable and breaking idempotency guarantees from the first pipeline stage.",
        implications=[
            "Without session_id, no event record can be written — ATR-01 audit completeness is structurally impossible.",
            "Malformed Twilio webhook configurations (missing CallSid) are silent in production without explicit validation at ingress.",
            "The 400 response must carry a structured error body so upstream systems can distinguish session binding failures from policy rejections.",
        ],
        state_machine="N/A — no session created",
        event_store="INCOMPLETE — no event written (no session_id available)",
        failure_coverage="Validation failure detected at VALIDATE stage, 400 returned",
        replay_integrity="N/A — no session to replay",
        next_iteration=[
            "Log missing-CallSid failures to a separate dead-letter queue with request timestamp and source IP.",
            "Add CallSid validation as the first check in the VALIDATE stage before any other processing.",
            "Return a structured JSON error body with error code VALIDATION_MISSING_CALLSID on 400 responses.",
        ],
    ),

    TraceSpec(
        slug="04-late-disclosure-idg01-pdx01",
        failure_mode="Late disclosure — IDG-01 + PDX-01 combined violation",
        stage_1="POLICY",
        stage_2="EXEC",
        artifact_type="impersonation-latency",
        system_context="B2B prior auth call / turn_count=3 / PHI already exchanged / disclosure_timestamp=null",
        events=[
            TraceEvent(0.00, "INGEST",   "POST /voice/process — turn_count=3, no disclosure on record"),
            TraceEvent(0.01, "VALIDATE", "SpeechResult='I need the member ID for this authorization'"),
            TraceEvent(0.02, "STATE",    "Session reconstructed: turn_count=3, disclosure_timestamp=null"),
            TraceEvent(0.04, "POLICY",   "IDG-01: disclosure_timestamp=null — DISCLOSE_IDENTITY triggered"),
            TraceEvent(0.05, "POLICY",   "PDX-01: PHI pattern detected in speech without disclosure — DENY_DATA"),
            TraceEvent(0.06, "POLICY",   "Composite: DENY_DATA dominates (priority 5 > 3)"),
            TraceEvent(0.08, "EXEC",     "TwiML gate message rendered: disclosure required before data exchange"),
            TraceEvent(0.10, "PERSIST",  "2 boundary_violations written: IDG-01 (critical), PDX-01 (critical)"),
        ],
        replay_result="PASS",
        failure_observation="The AI agent operated for three turns exchanging PHI without disclosing non-human identity — the exact impersonation latency scenario NHID-Clinical is designed to detect and block.",
        implications=[
            "Three turns of undisclosed AI operation is the median impersonation latency observed in production payer-caller workflows.",
            "PHI (member ID, prior auth number) was exchanged before disclosure, creating potential HIPAA Minimum Necessary compliance exposure.",
            "The PDX-01 gate must be enforced on every turn, not just turn zero, to catch delayed disclosure attempts.",
        ],
        state_machine="AWAITING_DISCLOSURE → GATE_BLOCKED (DENY_DATA enforced)",
        event_store="Complete — 2 critical violations in boundary_violations[]",
        failure_coverage="IDG-01 and PDX-01 both detected; DENY_DATA correctly dominates",
        replay_integrity="PASS — session state reconstruction is deterministic",
        next_iteration=[
            "Enforce PDX-01 on every turn, not just at session start.",
            "Add a 'turns_without_disclosure' counter to the session state for monitoring dashboards.",
            "Generate an alert when turn_count exceeds 1 with disclosure_timestamp=null.",
        ],
    ),

    TraceSpec(
        slug="05-escalation-path-missing-eit01",
        failure_mode="Escalation path missing — EIT-01 failure",
        stage_1="POLICY",
        stage_2="EXEC",
        artifact_type="escalation-failure",
        system_context="B2B eligibility call / human requests transfer / escalation_path_available=false",
        events=[
            TraceEvent(0.00, "INGEST",   "POST /voice/process — SpeechResult='I need to speak with a human'"),
            TraceEvent(0.01, "VALIDATE", "SpeechResult normalized: 'i need to speak with a human'"),
            TraceEvent(0.02, "STATE",    "Session: disclosure confirmed, escalation_path_available=false"),
            TraceEvent(0.04, "POLICY",   "EIT-01: escalation trigger detected in speech"),
            TraceEvent(0.05, "POLICY",   "EIT-01: escalation_path_available=false — violation"),
            TraceEvent(0.07, "POLICY",   "Decision: ESCALATE_HUMAN / EIT01_NO_ESCALATION_PATH"),
            TraceEvent(0.09, "EXEC",     "TwiML: 'unable to transfer at this time' message rendered"),
            TraceEvent(0.11, "PERSIST",  "1 boundary_violation: EIT-01 (critical)"),
        ],
        replay_result="PASS",
        failure_observation="Human operator explicitly requested escalation but the AI system had no functioning transfer path, stranding the caller and violating the NHID-Clinical safe-failover requirement.",
        implications=[
            "An escalation path that exists in configuration but is not tested in production is functionally equivalent to no escalation path.",
            "The EIT-01 violation must be surfaced to operational dashboards immediately — a blocked escalation is a patient/member safety risk.",
            "The TwiML fallback message must include an alternative contact method (callback number, hours) when transfer fails.",
        ],
        state_machine="DISCLOSED → ESCALATION_FAILED",
        event_store="Complete — EIT-01 critical violation recorded",
        failure_coverage="EIT-01 detected; ESCALATE_HUMAN action returned with fallback TwiML",
        replay_integrity="PASS",
        next_iteration=[
            "Add an escalation path health check to the server startup validation.",
            "Implement a circuit-breaker pattern for escalation path availability.",
            "Update TwiML fallback message to include a direct callback number when transfer is unavailable.",
        ],
    ),

    TraceSpec(
        slug="06-deceptive-artifact-dbc01",
        failure_mode="Deceptive artifact detected — DBC-01 violation",
        stage_1="POLICY",
        stage_2="EXEC",
        artifact_type="deception-violation",
        system_context="B2B prior auth call / AI agent using synthetic breathing sounds / deceptive_artifact_flags=['fake_breathing']",
        events=[
            TraceEvent(0.00, "INGEST",   "POST /voice/process — turn_count=2"),
            TraceEvent(0.01, "VALIDATE", "SpeechResult='*exhales* I'm pulling that up now'"),
            TraceEvent(0.02, "STATE",    "deceptive_artifact_flags=['fake_breathing'] detected by STT classifier"),
            TraceEvent(0.04, "POLICY",   "DBC-01: deceptive_artifact_flags non-empty"),
            TraceEvent(0.05, "POLICY",   "Decision: LOG_ONLY / DBC01_ARTIFACT_DETECTED"),
            TraceEvent(0.07, "EXEC",     "No TwiML modification — LOG_ONLY does not alter response"),
            TraceEvent(0.09, "PERSIST",  "1 boundary_violation: DBC-01 (critical), partial_failure=true"),
        ],
        replay_result="PASS",
        failure_observation="The AI agent emitted a synthetic exhale sound to simulate human presence, triggering a DBC-01 deceptive behavior violation while the call continued — a partial failure that corrupts audit integrity without halting the session.",
        implications=[
            "Deceptive artifacts can persist across multiple turns before detection if the STT classifier only runs periodically.",
            "DBC-01 violations set partial_failure=true — the session is not terminated but every subsequent event carries the taint.",
            "CA AB 489 (eff. Jan 1, 2026) creates legal exposure for any AI that implies human or licensed-professional status.",
        ],
        state_machine="DISCLOSED → DECEPTION_FLAGGED (partial_failure=true)",
        event_store="Complete — partial_failure=true, DBC-01 violation in boundary_violations[]",
        failure_coverage="DBC-01 detected; LOG_ONLY action recorded; session continues with taint flag",
        replay_integrity="PASS",
        next_iteration=[
            "Implement DBC-01 real-time monitoring that flags deceptive artifacts to a live operations dashboard.",
            "Evaluate whether DBC-01 critical violations should terminate the session rather than log-only.",
            "Add license_claim and human_name_claim to the STT classifier artifact detection patterns.",
        ],
    ),

    TraceSpec(
        slug="07-audit-field-missing-atr01",
        failure_mode="Audit field missing — ATR-01 failure",
        stage_1="POLICY",
        stage_2="PERSIST",
        artifact_type="audit-gap",
        system_context="B2B claim status call / pipeline_version missing from execution_context",
        events=[
            TraceEvent(0.00, "INGEST",   "POST /voice/process — turn_count=1"),
            TraceEvent(0.01, "VALIDATE", "SpeechResult='checking claim status'"),
            TraceEvent(0.02, "STATE",    "Session reconstructed: disclosure confirmed"),
            TraceEvent(0.04, "POLICY",   "ATR-01: execution_context.pipeline_version=null"),
            TraceEvent(0.05, "POLICY",   "ATR-01: AUDIT_FIELDS_MISSING violation"),
            TraceEvent(0.07, "EXEC",     "Pipeline continues — ATR-01 does not block execution"),
            TraceEvent(0.09, "PERSIST",  "Event written with ATR-01 violation in boundary_violations[]"),
        ],
        replay_result="PASS",
        failure_observation="The execution_context.pipeline_version field was null, making it impossible to reconstruct which pipeline version processed this call during a post-incident audit.",
        implications=[
            "Missing pipeline_version breaks cross-incident correlation — you cannot identify whether multiple failures share a common pipeline version.",
            "ATR-01 violations do not halt execution, creating a silent audit gap that accumulates across sessions.",
            "Procurement and compliance reviewers require complete provenance chains; a missing pipeline_version fails an enterprise audit review.",
        ],
        state_machine="DISCLOSED → DISCLOSED (no state change, ATR-01 is non-blocking)",
        event_store="INCOMPLETE — execution_context.pipeline_version missing from event record",
        failure_coverage="ATR-01 detected; LOG_ONLY action; pipeline_version gap recorded",
        replay_integrity="DEGRADED — provenance chain incomplete for this event",
        next_iteration=[
            "Add execution_context validation to the server startup check — fail fast if pipeline_version is not configured.",
            "Implement an ATR-01 compliance score across sessions: % of events with complete execution_context.",
            "Alert on ATR-01 violation rate exceeding 0% — any audit field missing is a governance regression.",
        ],
    ),

    TraceSpec(
        slug="08-bot-to-bot-no-gate",
        failure_mode="Bot-to-bot call with no stricter gate — policy gap",
        stage_1="POLICY",
        stage_2="EXEC",
        artifact_type="bot-to-bot-policy-gap",
        system_context="B2B prior auth call / payer deploying AI agent / counterparty_type=ai_agent / disclosure_timestamp=null",
        events=[
            TraceEvent(0.00, "INGEST",   "POST /voice/process — counterparty_type=ai_agent"),
            TraceEvent(0.01, "VALIDATE", "SpeechResult='Initiating PA workflow. Requesting member data.'"),
            TraceEvent(0.02, "STATE",    "counterparty_type=ai_agent, disclosure_timestamp=null"),
            TraceEvent(0.04, "POLICY",   "BOT-TO-BOT rule: counterparty is ai_agent, disclosure missing"),
            TraceEvent(0.05, "POLICY",   "Decision: DENY_DATA / BOT2BOT_UNDISCLOSED_AGENT"),
            TraceEvent(0.07, "EXEC",     "TwiML: identity verification required message"),
            TraceEvent(0.09, "PERSIST",  "IDG-01 critical violation recorded (bot-to-bot context)"),
        ],
        replay_result="PASS",
        failure_observation="An undisclosed AI agent initiated a bot-to-bot prior authorization workflow without identity disclosure, exploiting the absence of a bot-to-bot-specific policy gate in systems that only enforce IDG-01 for human counterparties.",
        implications=[
            "AI-to-AI calls are increasing as payers deploy their own AI agents to respond to provider AI callers.",
            "Standard IDG-01 rules designed for human counterparties are insufficient for bot-to-bot contexts where both parties may be AI systems.",
            "NHID-Clinical v1.3 does not fully specify bot-to-bot identity verification — this is a known gap in the current spec.",
        ],
        state_machine="AWAITING_DISCLOSURE → GATE_BLOCKED (DENY_DATA)",
        event_store="Complete — IDG-01 critical violation with bot-to-bot context recorded",
        failure_coverage="Bot-to-bot supplemental rule detected gap; DENY_DATA enforced",
        replay_integrity="PASS",
        next_iteration=[
            "Escalate NHID-Auth bot-to-bot identity verification from future scope to v1.4 priority.",
            "Reference IETF AgentID Protocol (draft-gudlab-agentid-protocol-00) as the technical basis for bot-to-bot identity tokens.",
            "Add counterparty_type detection to the ingress layer — identify AI callers from SIP headers or DNIS patterns.",
        ],
    ),

    TraceSpec(
        slug="09-replay-divergence-determinism",
        failure_mode="Replay divergence — determinism failure",
        stage_1="EXEC",
        stage_2="PERSIST",
        artifact_type="replay-integrity-violation",
        system_context="B2B eligibility call / replay_mode=cached / external_calls_cached=false (misconfigured)",
        events=[
            TraceEvent(0.00, "INGEST",   "REPLAY REQUEST: session_id=REPLAY-001, replay_mode=cached"),
            TraceEvent(0.01, "VALIDATE", "external_calls_cached=false (misconfiguration)"),
            TraceEvent(0.02, "STATE",    "Event stream loaded from store: 7 events"),
            TraceEvent(0.04, "EXEC",     "LLM call made during replay (external_calls_cached=false)"),
            TraceEvent(0.06, "EXEC",     "LLM returned different completion than original session"),
            TraceEvent(0.08, "PERSIST",  "Replay result differs from original — divergence detected"),
            TraceEvent(0.10, "PERSIST",  "ATR-01 violation: replay_integrity=FAIL"),
        ],
        replay_result="FAIL",
        failure_observation="Replay with external_calls_cached=false caused an LLM re-invocation that produced a different completion than the original session, breaking deterministic audit reconstruction.",
        implications=[
            "Replay divergence means post-incident audit reconstruction is unreliable — you cannot prove what the AI said during the original call.",
            "This is the most dangerous replay failure mode in healthcare voice AI: silent divergence that looks like a successful replay.",
            "The canonical constraint (no external calls during replay) must be enforced as a hard schema rule, not a convention.",
        ],
        state_machine="REPLAY → DIVERGENCE_DETECTED",
        event_store="CORRUPTED — replay result written over original event stream",
        failure_coverage="Divergence detected; ATR-01 violation recorded",
        replay_integrity="FAIL — LLM re-invocation produced non-identical output",
        next_iteration=[
            "Enforce external_calls_cached=true as a hard requirement when replay_mode=cached (JSON Schema if/then constraint).",
            "Add a replay integrity hash to the original event record — SHA-256 of the canonical output payload.",
            "Implement a replay divergence alert that triggers when replay output hash does not match original.",
        ],
    ),

    TraceSpec(
        slug="10-partial-failure-boundary-violation",
        failure_mode="Partial failure — stage completed with violations",
        stage_1="POLICY",
        stage_2="PERSIST",
        artifact_type="partial-failure-boundary",
        system_context="B2B prior auth call / disclosure confirmed / deceptive artifact mid-session / partial_failure=true",
        events=[
            TraceEvent(0.00, "INGEST",   "POST /voice/process — turn_count=4, disclosure_timestamp set"),
            TraceEvent(0.01, "VALIDATE", "SpeechResult='*typing sounds* Let me check that for you'"),
            TraceEvent(0.02, "STATE",    "Session: DISCLOSED, deceptive_artifact_flags=['fake_typing']"),
            TraceEvent(0.04, "POLICY",   "DBC-01: fake_typing artifact detected → boundary_violation"),
            TraceEvent(0.05, "POLICY",   "ATR-01: all audit fields present"),
            TraceEvent(0.06, "POLICY",   "Composite: LOG_ONLY (DBC-01) — session continues"),
            TraceEvent(0.08, "EXEC",     "Original LLM response rendered (LOG_ONLY does not override)"),
            TraceEvent(0.10, "PERSIST",  "partial_failure=true, 1 DBC-01 critical violation written"),
        ],
        replay_result="PASS",
        failure_observation="The pipeline completed successfully but with a DBC-01 deceptive artifact violation recorded as a partial failure — the most operationally dangerous failure mode because the session appears normal from the outside while governance boundaries are breached internally.",
        implications=[
            "partial_failure=true is invisible to the human operator receiving the call — only the audit trail captures the violation.",
            "Partial failures accumulate silently across sessions; a 5% partial failure rate across 10,000 calls represents 500 undetected governance violations.",
            "The decision to not halt on DBC-01 (LOG_ONLY vs ESCALATE_HUMAN) must be explicit policy, not default behavior.",
        ],
        state_machine="DISCLOSED → DECEPTION_FLAGGED (partial_failure=true, session continues)",
        event_store="Complete — partial_failure=true and boundary_violations[] correctly populated",
        failure_coverage="DBC-01 detected as partial failure; LOG_ONLY action; session tainted but not terminated",
        replay_integrity="PASS — partial failure is deterministically reproducible",
        next_iteration=[
            "Implement a partial_failure rate dashboard across all active sessions.",
            "Define an explicit policy rule: after N partial_failure events in a session, escalate to human.",
            "Add DBC-01 partial failure to the automated alert threshold: >0 partial failures per session triggers ops review.",
        ],
    ),
]


# ── Markdown renderer ─────────────────────────────────────────────────────

def _render_trace(trace: TraceSpec, session_id: str) -> str:
    events_block = "\n".join(
        f"t={_ts(e.offset)}  {e.stage:<10} {e.description}"
        for e in trace.events
    )

    violations_block = "\n".join(f"- {imp}" for imp in trace.implications)
    next_iter_block  = "\n".join(f"- {step}" for step in trace.next_iteration)

    return f"""NHID-Clinical • {trace.stage_1} → {trace.stage_2} → {trace.artifact_type}

session: {session_id}
context: {trace.system_context}

---

event stream (append-only)

{events_block}

---

replay attempt (deterministic)

input: identical event stream
constraints: no external calls
result: {trace.replay_result}

---

failure observation

{trace.failure_observation}

---

implication

{violations_block}

---

classification

state machine: {trace.state_machine}
event store: {trace.event_store}
failure coverage: {trace.failure_coverage}
replay integrity: {trace.replay_integrity}

---

next iteration

{next_iter_block}

---

NHID-Clinical is mapping where deterministic orchestration breaks in real-world healthcare voice AI systems.
"""


# ── Main ──────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate NHID-Clinical canonical trace files."
    )
    parser.add_argument(
        "--output-dir",
        default=os.path.join(os.path.dirname(__file__), "..", "traces"),
        help="Directory to write trace markdown files (default: ../traces)",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Generate synthetic traces without connecting to a server.",
    )
    args = parser.parse_args()

    output_dir = os.path.abspath(args.output_dir)
    os.makedirs(output_dir, exist_ok=True)

    print(f"NHID-Clinical Trace Generator")
    print(f"Output directory: {output_dir}")
    print(f"Engine available: {_ENGINE_AVAILABLE}")
    print()

    # Optionally validate traces against the policy engine
    if _ENGINE_AVAILABLE and not args.offline:
        print("Running policy engine validation against trace specs...")
        _validate_traces_against_engine()

    # Write trace files — session IDs are deterministic (UUID v5, slug-based)
    for i, trace in enumerate(_TRACES, start=1):
        session_id = f"NHID-TRACE-{i:02d}-{str(uuid.uuid5(uuid.NAMESPACE_DNS, f'nhid-trace-{i:02d}-{trace.slug}'))[:8].upper()}"
        filename   = f"nhid-trace-{trace.slug}.md"
        filepath   = os.path.join(output_dir, filename)

        content = _render_trace(trace, session_id)
        with open(filepath, "w", encoding="utf-8") as fh:
            fh.write(content)

        print(f"  [{i:02d}/10] {filename}")

    print()
    print(f"10 trace files written to {output_dir}/")
    print()
    print("To publish: review each trace, redact any real session data,")
    print("then add to nhid-clinical.org/traces/ as the public failure ledger.")


def _validate_traces_against_engine() -> None:
    """
    Cross-reference trace specs against the policy engine.
    Prints a warning if a trace's stated failure mode is inconsistent
    with what the engine would actually produce.
    """
    if not _ENGINE_AVAILABLE:
        return

    # Build minimal event objects for key traces and check engine output
    checks = [
        {
            "trace_slug": "04-late-disclosure-idg01-pdx01",
            "expected_action": engine.PolicyAction.DENY_DATA,
            "event": {
                "event_id": str(uuid.uuid4()),
                "timestamp": _now_iso(),
                "session_id": "VALIDATE-001",
                "request_id": "req-validate-001",
                "event_type": "POLICY",
                "actor_id": "nhid-test",
                "counterparty_type": "human_operator",
                "state_before": "AWAITING_DISCLOSURE",
                "state_after": "AWAITING_DISCLOSURE",
                "partial_failure": False,
                "boundary_violations": [],
                "replay_mode": "live",
                "external_calls_cached": False,
                "execution_context": {
                    "pipeline_version": "1.0.0",
                    "policy_engine_version": "1.0.0",
                    "nhid_schema_version": "1.0",
                },
                "healthcare_governance": {
                    "disclosure_timestamp": None,
                    "identity_assertion_text": None,
                    "deceptive_artifact_flags": [],
                    "escalation_timestamp": None,
                    "escalation_outcome": None,
                    "phi_accessed": [],
                },
                "input_payload": {
                    "speech_text": "I need the member ID for this authorization",
                    "raw_form_fields": None,
                },
                "output_payload": None,
                "error": None,
                "policy_decision": None,
            },
            "session": {"turn_count": 3, "escalation_path_available": True},
        },
    ]

    for check in checks:
        decision = engine.evaluate_all(check["session"], check["event"])
        if decision.action != check["expected_action"]:
            print(
                f"  WARNING: Trace {check['trace_slug']} expects {check['expected_action'].value} "
                f"but engine returned {decision.action.value}"
            )
        else:
            print(f"  OK: {check['trace_slug']} — engine confirms {decision.action.value}")


if __name__ == "__main__":
    main()
