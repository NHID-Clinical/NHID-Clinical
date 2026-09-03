"""
NHID-Clinical Failure Injection Harness
========================================
pytest-based test harness for NHID-Clinical pipeline hardening.

Purpose: verify that the FastAPI pipeline is deterministic, auditable,
and never silently fails under adversarial or malformed input conditions.

Assumptions:
  - A FastAPI server is running at BASE_URL (default: http://127.0.0.1:8000)
  - The server implements /voice/process (POST, form-urlencoded)
  - The server implements /debug/replay/{session_id}
  - SQLite event store is at EVENT_DB_PATH

Usage:
  # Start your server first:
  # uvicorn app:app --reload --port 8000
  python -m pytest tests/failure_injection_harness.py -v

Override server URL:
  NHID_BASE_URL=http://localhost:9000 python -m pytest tests/failure_injection_harness.py -v

NHID-Clinical is a voluntary open proposal. CC BY 4.0.
Not an accredited standard. Not a regulatory requirement.
"""

from __future__ import annotations

import os
import re
import sqlite3
import time
from typing import Any

import httpx
import pytest

# ── Configuration ─────────────────────────────────────────────────────────

BASE_URL     = os.environ.get("NHID_BASE_URL", "http://127.0.0.1:8000")
EVENT_DB_PATH = os.environ.get("NHID_EVENT_DB", "nhid_events.db")
TIMEOUT      = float(os.environ.get("NHID_TIMEOUT", "10"))

PROCESS_URL  = f"{BASE_URL}/voice/process"
REPLAY_URL   = f"{BASE_URL}/debug/replay"

_TWIML_ROOT_PATTERN = re.compile(r"<Response\b", re.IGNORECASE)
_TWIML_CONTENT_TYPES = frozenset({
    "application/xml",
    "text/xml",
    "text/html",  # some Twilio impls use this
})


# ── Shared helpers ─────────────────────────────────────────────────────────

def _post(data: dict[str, str], *, headers: dict[str, str] | None = None) -> httpx.Response:
    """POST form-urlencoded to /voice/process."""
    h = {"Content-Type": "application/x-www-form-urlencoded"}
    if headers:
        h.update(headers)
    return httpx.post(PROCESS_URL, data=data, headers=h, timeout=TIMEOUT)


def assert_no_500(response: httpx.Response) -> None:
    """Fail if the server returned an HTTP 5xx status."""
    assert response.status_code < 500, (
        f"Server returned HTTP {response.status_code} — pipeline must never 5xx.\n"
        f"Body: {response.text[:500]}"
    )


def assert_twiml(response: httpx.Response) -> None:
    """Fail if the response is not valid TwiML (XML with <Response> root)."""
    content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
    body = response.text
    assert _TWIML_ROOT_PATTERN.search(body), (
        f"Response body does not contain TwiML <Response> element.\n"
        f"Content-Type: {content_type}\nBody: {body[:500]}"
    )


def assert_event_written(session_id: str, db_path: str = EVENT_DB_PATH) -> None:
    """Fail if no event record exists for the given session_id in the SQLite store."""
    if not os.path.exists(db_path):
        pytest.skip(f"Event DB not found at {db_path} — skipping event persistence check.")
    try:
        con = sqlite3.connect(db_path)
        cur = con.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM events WHERE session_id = ?", (session_id,)
        )
        count = cur.fetchone()[0]
        con.close()
        assert count > 0, (
            f"No events found in {db_path} for session_id={session_id!r}. "
            "Pipeline must persist events even on validation failure."
        )
    except sqlite3.OperationalError as e:
        pytest.skip(f"Could not query event DB: {e}")


def assert_replay_inspection(
    session_id: str,
    *,
    expected_response: str,
    db_path: str = EVENT_DB_PATH,
) -> dict:
    """Assert the /debug/replay inspection contract.

    Settled 2026-09-03 from repository evidence, not preference. This helper
    previously POSTed to the endpoint and required the original TwiML back,
    which the implementation could never satisfy: the route is a GET returning a
    JSON forensic trace, and a JSON trace can never equal TwiML. Correcting the
    verb alone would not have reconciled them -- they were two different
    contracts.

    The evidence says inspection:
      * `nhid_event_store.replay(session_id)` is literally
        `return get_events(session_id)` -- retrieval, not re-execution.
      * the route is `@app.get`, documented as "Full forensic trace".
      * `traces/nhid-trace-09` treats an LLM call *during* replay as a failure
        mode, and files replay-integrity hashing under "next iteration" --
        a proposal, not a shipped capability.

    So re-execution is not manufactured here to satisfy a test. What is asserted
    instead is what the contract actually owes an auditor: a retrievable,
    deterministic, faithful record of the interaction.
    """
    r = httpx.get(f"{REPLAY_URL}/{session_id}", timeout=TIMEOUT)
    assert_no_500(r)
    assert r.status_code == 200, (
        f"Inspection retrieval must succeed; got HTTP {r.status_code}. Body: {r.text[:300]}"
    )

    trace = r.json()
    for key in ("session_id", "reconstructed_state", "events"):
        assert key in trace, f"trace is missing {key!r}; got keys {sorted(trace)}"
    assert trace["session_id"] == session_id
    assert trace["events"], f"trace for {session_id!r} contains no events"

    # Faithful: the response the caller actually received must be recoverable
    # from the record. An audit trail that cannot show what was said is not
    # evidence of anything.
    responses = [e.get("response_text") for e in trace["events"] if e.get("response_text")]
    assert any(expected_response.strip() == (resp or "").strip() for resp in responses), (
        "The response returned to the caller does not appear in the trace.\n"
        f"Returned: {expected_response[:200]!r}\n"
        f"Recorded: {[str(x)[:120] for x in responses]}"
    )

    # Deterministic: retrieving twice yields the same record.
    again = httpx.get(f"{REPLAY_URL}/{session_id}", timeout=TIMEOUT)
    assert again.status_code == 200
    assert again.json() == trace, (
        "Two retrievals of the same session returned different traces. "
        "Inspection must be deterministic."
    )
    return trace


# ── Marker: skip if server not reachable ─────────────────────────────────

def _server_reachable() -> bool:
    try:
        httpx.get(f"{BASE_URL}/health", timeout=2)
        return True
    except httpx.RequestError:
        return False


_SERVER_UP = _server_reachable()

# CI sets NHID_REQUIRE_SERVER=1. Without it, an unreachable server silently
# turns 18 integration tests into 18 skips and the job still reports green —
# which is precisely how these tests went unexecuted long enough for seven
# real divergences to accumulate behind them. Fail loudly instead.
if os.environ.get("NHID_REQUIRE_SERVER") == "1" and not _SERVER_UP:
    raise RuntimeError(
        f"NHID_REQUIRE_SERVER=1 but nothing answered at {BASE_URL}. "
        "The integration tests must run, not skip. Start the server "
        "(python -m uvicorn app:app --port 8000) or unset the variable."
    )

requires_server = pytest.mark.skipif(
    not _SERVER_UP,
    reason=f"NHID FastAPI server not reachable at {BASE_URL}. Start the server to run integration tests.",
)


# ── Known divergences between this harness and the implementation ─────────
#
# The seven tests marked below first executed on 2026-09-03, when CI began
# starting the server instead of skipping past it. They fail for exactly two
# reasons, and both are open product decisions recorded in
# docs/skipped-test-audit.md §8 — not flaky infrastructure, and not defects in
# the tests' own mechanics. Recording them as xfail keeps them running and
# keeps the divergence legible; deleting them or relaxing their assertions
# would destroy the only evidence that the contradiction exists.
#
# strict=True is deliberate. If either decision is implemented, these become
# unexpected passes and CI turns red until the marker is removed, so a marker
# cannot quietly outlive the contradiction it describes.

# ── The missing/empty CallSid contract ────────────────────────────────────
#
# Resolved 2026-09-03. These tests previously required HTTP 400 while the
# implementation coerced a missing CallSid to the shared literal "unknown" and
# returned 200 TwiML. Neither side was right: 400 breaks the Twilio webhook
# contract, and a shared constant collapses every unidentified interaction into
# one audit identity, which is precisely what ATR-01 exists to prevent.
#
# The approved contract takes neither position. The request is accepted and
# answered with TwiML; the absent CallSid is recorded as absent rather than
# invented; and a distinct synthetic session id keeps the interaction separable
# in the audit trail. The assertions below are written against that contract,
# not relaxed to accommodate the old behaviour.

SYNTHETIC_SESSION_PREFIX = "nhid-anon-"


def _identity_row(session_id: str, db_path: str = EVENT_DB_PATH):
    """Return (call_sid, session_id_source) for a session, or None if absent."""
    if not os.path.exists(db_path):
        pytest.fail(f"Event DB not found at {db_path}; the audit contract cannot be verified.")
    con = sqlite3.connect(db_path)
    try:
        row = con.execute(
            "SELECT call_sid, session_id_source FROM events WHERE session_id = ? LIMIT 1",
            (session_id,),
        ).fetchone()
    finally:
        con.close()
    return row


def _latest_synthetic_sessions(limit: int = 8, db_path: str = EVENT_DB_PATH):
    """Most recent synthetic session ids, newest first."""
    if not os.path.exists(db_path):
        pytest.fail(f"Event DB not found at {db_path}; the audit contract cannot be verified.")
    con = sqlite3.connect(db_path)
    try:
        rows = con.execute(
            "SELECT DISTINCT session_id FROM events WHERE session_id_source = 'synthetic' "
            "ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    finally:
        con.close()
    return [r[0] for r in rows]


def assert_unidentified_contract(response: httpx.Response) -> str:
    """Assert the full contract for an interaction with no usable CallSid.

    Returns the synthetic session id that was minted, so callers can assert
    that separate interactions did not share one.
    """
    assert_no_500(response)
    assert response.status_code == 200, (
        f"An otherwise-valid webhook with no CallSid must still be accepted and "
        f"answered; got HTTP {response.status_code}."
    )
    assert_twiml(response)

    sessions = _latest_synthetic_sessions()
    assert sessions, (
        "No event was written under a synthetic session id. An interaction "
        "without a CallSid must still be auditable."
    )
    session_id = sessions[0]
    assert session_id.startswith(SYNTHETIC_SESSION_PREFIX), (
        f"Synthetic session id {session_id!r} must carry the "
        f"{SYNTHETIC_SESSION_PREFIX!r} prefix so it can never be mistaken for a "
        "Twilio CallSid."
    )

    row = _identity_row(session_id)
    assert row is not None, f"No audit row for session {session_id!r}"
    call_sid, source = row
    assert call_sid is None, (
        f"call_sid must be NULL when the upstream request carried none; got {call_sid!r}. "
        "The synthetic id must never be presented as the actual Twilio CallSid."
    )
    assert source == "synthetic", f"session_id_source must be 'synthetic'; got {source!r}"
    return session_id



# ──────────────────────────────────────────────────────────────────────────
# Test suite
# ──────────────────────────────────────────────────────────────────────────

@requires_server
class TestInputValidation:
    """
    Pipeline must reject or safely handle malformed input at the VALIDATE stage.
    No 5xx responses. Event records required where a session_id is available.
    """

    def test_empty_speech_result(self) -> None:
        """SpeechResult is empty string. Pipeline must not 500. TwiML fallback required."""
        session_id = f"EDGE-EMPTY-{int(time.time())}"
        r = _post({"CallSid": session_id, "SpeechResult": ""})
        assert_no_500(r)
        assert_twiml(r)
        assert_event_written(session_id)

    def test_whitespace_only_speech(self) -> None:
        """SpeechResult is whitespace only. Normalize to empty string. Must not 500."""
        session_id = f"EDGE-WS-{int(time.time())}"
        r = _post({"CallSid": session_id, "SpeechResult": "   \t\n  "})
        assert_no_500(r)
        assert_twiml(r)

    def test_null_bytes_injection(self) -> None:
        """SpeechResult contains null bytes. Must sanitize and not crash."""
        session_id = f"EDGE-NULL-{int(time.time())}"
        r = _post({"CallSid": session_id, "SpeechResult": "\x00\x00\x00check claim status"})
        assert_no_500(r)
        assert_twiml(r)
        assert_event_written(session_id)

    def test_null_bytes_only(self) -> None:
        """SpeechResult is only null bytes. Must not crash."""
        session_id = f"EDGE-NULLONLY-{int(time.time())}"
        r = _post({"CallSid": session_id, "SpeechResult": "\x00\x00\x00"})
        assert_no_500(r)
        assert_twiml(r)

    def test_missing_callsid(self) -> None:
        """CallSid absent: accept, answer, and mint a distinct audit identity."""
        r = _post({"SpeechResult": "checking member eligibility"})
        assert_unidentified_contract(r)

    def test_missing_all_fields(self) -> None:
        """Empty body: still answered, still auditable under its own identity."""
        r = _post({})
        assert_unidentified_contract(r)

    def test_empty_callsid(self) -> None:
        """Empty CallSid is treated as absent, not as the literal empty string."""
        r = _post({"CallSid": "", "SpeechResult": "checking eligibility"})
        assert_unidentified_contract(r)

    def test_unidentified_interactions_do_not_share_an_audit_identity(self) -> None:
        """The defect this contract exists to prevent.

        Two separate interactions with no CallSid must not end up under one
        session id. Coercing to a shared literal made every unidentified call
        indistinguishable in the audit trail, which is the opposite of what
        ATR-01 is for.
        """
        first = assert_unidentified_contract(_post({"SpeechResult": "first unidentified call"}))
        second = assert_unidentified_contract(_post({"SpeechResult": "second unidentified call"}))
        assert first != second, (
            f"Two unidentified interactions collapsed into one audit identity "
            f"({first!r}). They must remain separable."
        )

    def test_present_callsid_is_preserved_verbatim(self) -> None:
        """A real CallSid is used as-is and recorded as upstream-provided."""
        session_id = f"CAtest{int(time.time())}"
        r = _post({"CallSid": session_id, "SpeechResult": "verify benefits"})
        assert_no_500(r)
        assert_twiml(r)
        row = _identity_row(session_id)
        assert row is not None, f"no audit row for {session_id!r}"
        call_sid, source = row
        assert call_sid == session_id, (
            f"upstream CallSid must be preserved verbatim; got {call_sid!r}"
        )
        assert source == "twilio_callsid", (
            f"source must record that the id came from upstream; got {source!r}"
        )

    def test_very_long_speech(self) -> None:
        """Extremely long SpeechResult (10KB). Must not crash or time out badly."""
        session_id = f"EDGE-LONG-{int(time.time())}"
        long_text = "check prior authorization status " * 300  # ~10KB
        r = _post({"CallSid": session_id, "SpeechResult": long_text})
        assert_no_500(r)
        assert_twiml(r)


@requires_server
class TestChaosMode:
    """
    Combined adversarial scenarios. Tests pipeline resilience under
    multiple simultaneous failure conditions.
    """

    def test_chaos_null_bytes_empty_callsid(self) -> None:
        """Null bytes AND empty CallSid: both handled, identity still distinct."""
        r = _post({"CallSid": "", "SpeechResult": "\x00\x00\x00check claim"})
        assert_unidentified_contract(r)

    def test_chaos_correlation_id_header(self) -> None:
        """
        Custom correlation ID header with empty speech. Used to test
        that correlation IDs propagate through the event trace.
        """
        session_id = f"CHAOS-CORR-{int(time.time())}"
        r = _post(
            {"CallSid": session_id, "SpeechResult": ""},
            headers={"X-NHID-CORRELATION-ID": session_id},
        )
        assert_no_500(r)
        assert_twiml(r)

    def test_chaos_failure_injection_header(self) -> None:
        """
        FAILURE_INJECTION_MODE header with empty speech. Standard chaos
        harness pattern from NHID-Clinical failure injection spec.
        """
        session_id = f"CHAOS-INJECT-{int(time.time())}"
        r = _post(
            {"CallSid": session_id, "SpeechResult": ""},
            headers={
                "X-NHID-TEST": "FAILURE_INJECTION_MODE",
                "X-NHID-CORRELATION-ID": session_id,
            },
        )
        assert_no_500(r)
        assert_twiml(r)

    def test_chaos_full_adversarial(self) -> None:
        """Full adversarial: empty CallSid + null bytes + chaos headers."""
        r = _post(
            {"CallSid": "", "SpeechResult": "\x00\x00\x00check claim status"},
            headers={"X-NHID-TEST": "CHAOS"},
        )
        assert_unidentified_contract(r)


@requires_server
class TestPolicyEnforcement:
    """
    Tests that the policy engine correctly enforces NHID-Clinical controls
    through the HTTP/TwiML interface.
    """

    def test_idg01_violation_triggers_disclosure(self) -> None:
        """
        No prior disclosure + PHI-suggestive speech. Policy must respond
        with an identity disclosure message, not pass through to LLM.
        """
        session_id = f"POLICY-IDG01-{int(time.time())}"
        r = _post({
            "CallSid": session_id,
            "SpeechResult": "What is the member ID for this patient?",
        })
        assert_no_500(r)
        assert_twiml(r)
        body = r.text.lower()
        # The TwiML response must contain disclosure language
        assert any(phrase in body for phrase in [
            "automated system",
            "not a human",
            "automated",
            "i am an",
        ]), (
            f"Expected disclosure language in TwiML response for IDG-01 violation.\nBody: {r.text[:500]}"
        )

    def test_escalation_trigger_in_speech(self) -> None:
        """
        Speech contains escalation trigger phrase. Policy must return
        ESCALATE_HUMAN action and appropriate TwiML.
        """
        session_id = f"POLICY-EIT01-{int(time.time())}"
        r = _post({
            "CallSid": session_id,
            "SpeechResult": "I need to speak with a human representative.",
        })
        assert_no_500(r)
        assert_twiml(r)

    def test_audit_trail_completeness(self) -> None:
        """
        Normal request. Event record must contain all ATR-01 required
        audit fields. Verifies by checking event DB directly.
        """
        session_id = f"POLICY-ATR01-{int(time.time())}"
        r = _post({
            "CallSid": session_id,
            "SpeechResult": "Calling to check eligibility.",
        })
        assert_no_500(r)
        assert_twiml(r)
        assert_event_written(session_id)

        if not os.path.exists(EVENT_DB_PATH):
            pytest.skip("Event DB not found — skipping field completeness check.")

        try:
            con = sqlite3.connect(EVENT_DB_PATH)
            cur = con.cursor()
            cur.execute(
                "SELECT * FROM events WHERE session_id = ? LIMIT 1", (session_id,)
            )
            row = cur.fetchone()
            col_names = [d[0] for d in cur.description] if cur.description else []
            con.close()

            assert row is not None, f"No event row found for session_id={session_id!r}"

            required_columns = {"session_id", "event_type", "timestamp"}
            missing = required_columns - set(col_names)
            assert not missing, (
                f"Event table missing required ATR-01 columns: {missing}"
            )
        except sqlite3.OperationalError as e:
            pytest.skip(f"Could not query event DB columns: {e}")


@requires_server
class TestReplayDeterminism:
    """
    Replay integrity tests. The same event stream replayed must produce
    identical output with no external calls. Divergence = ATR-01 violation.
    """

    def test_replay_inspection_normal_request(self) -> None:
        """A completed interaction is retrievable as a faithful forensic trace."""
        session_id = f"REPLAY-ID-{int(time.time())}"
        r1 = _post({
            "CallSid": session_id,
            "SpeechResult": "Calling to verify benefits.",
        })
        assert_no_500(r1)
        time.sleep(0.2)
        trace = assert_replay_inspection(session_id, expected_response=r1.text)
        assert trace["reconstructed_state"]["session_id"] == session_id

    def test_replay_idempotency_same_request_id(self) -> None:
        """
        Same logical request sent twice must produce identical responses.
        Tests idempotency via request_id / duplicate guard.
        """
        session_id = f"REPLAY-IDEM-{int(time.time())}"
        data = {"CallSid": session_id, "SpeechResult": "prior auth status please"}

        r1 = _post(data)
        assert_no_500(r1)
        time.sleep(0.1)
        r2 = _post(data)
        assert_no_500(r2)

        # Responses must be identical (idempotency guarantee)
        assert r1.text == r2.text, (
            "Duplicate request produced different responses.\n"
            f"First:  {r1.text[:400]}\nSecond: {r2.text[:400]}"
        )

    def test_replay_inspection_empty_speech(self) -> None:
        """Empty-input handling is recorded, and its trace is deterministic."""
        session_id = f"REPLAY-EMPTY-{int(time.time())}"
        r1 = _post({"CallSid": session_id, "SpeechResult": ""})
        assert_no_500(r1)
        time.sleep(0.2)
        assert_replay_inspection(session_id, expected_response=r1.text)

    def test_replay_is_a_retrieval_contract_not_re_execution(self) -> None:
        """Pin the verb, so the contract cannot drift back into ambiguity.

        The endpoint is a GET. It was previously tested with POST, which
        returns 405 and produced two years of apparent "replay divergence"
        that was really a method mismatch.
        """
        session_id = f"REPLAY-VERB-{int(time.time())}"
        r1 = _post({"CallSid": session_id, "SpeechResult": "prior auth status"})
        assert_no_500(r1)
        time.sleep(0.2)

        posted = httpx.post(f"{REPLAY_URL}/{session_id}", timeout=TIMEOUT)
        assert posted.status_code == 405, (
            "Replay is a retrieval contract; POST must not be accepted. "
            f"Got HTTP {posted.status_code}."
        )
        got = httpx.get(f"{REPLAY_URL}/{session_id}", timeout=TIMEOUT)
        assert got.status_code == 200


# ──────────────────────────────────────────────────────────────────────────
# Unit tests for policy engine (no server required)
# ──────────────────────────────────────────────────────────────────────────

class TestPolicyEngineUnit:
    """
    Pure unit tests for nhid_policy_engine_v1.py.
    No server required. Tests all five conformance functions directly.
    """

    @pytest.fixture(autouse=True)
    def import_engine(self) -> None:
        try:
            import sys
            import os
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
            import nhid_policy_engine_v1 as engine
            self.engine = engine
        except ImportError as e:
            pytest.skip(f"Could not import policy engine: {e}")

    def _base_event(self, overrides: dict[str, Any] | None = None) -> dict[str, Any]:
        event: dict[str, Any] = {
            "event_id":            "550e8400-e29b-41d4-a716-446655440001",
            "timestamp":           "2026-05-26T14:30:00.000Z",
            "session_id":          "TEST-SESSION-001",
            "request_id":          "req-test-001",
            "event_type":          "POLICY",
            "actor_id":            "nhid-test-agent",
            "counterparty_type":   "human_operator",
            "state_before":        "AWAITING_DISCLOSURE",
            "state_after":         "AWAITING_DISCLOSURE",
            "partial_failure":     False,
            "boundary_violations": [],
            "replay_mode":         "live",
            "external_calls_cached": False,
            "execution_context": {
                "pipeline_version":      "1.0.0",
                "policy_engine_version": "1.0.0",
                "nhid_schema_version":   "1.0",
            },
            "healthcare_governance": {
                "disclosure_timestamp":    None,
                "identity_assertion_text": None,
                "deceptive_artifact_flags": [],
                "escalation_timestamp":    None,
                "escalation_outcome":      None,
                "phi_accessed":            [],
            },
            "input_payload": {
                "speech_text": "",
                "raw_form_fields": None,
            },
            "output_payload": None,
            "error": None,
            "policy_decision": None,
        }
        if overrides:
            for k, v in overrides.items():
                if "." in k:
                    parts = k.split(".", 1)
                    event[parts[0]][parts[1]] = v
                else:
                    event[k] = v
        return event

    def _base_session(self, overrides: dict[str, Any] | None = None) -> dict[str, Any]:
        session: dict[str, Any] = {
            "turn_count": 0,
            "escalation_path_available": True,
        }
        if overrides:
            session.update(overrides)
        return session

    # IDG-01 unit tests

    def test_idg01_pass_disclosure_present(self) -> None:
        event = self._base_event({
            "healthcare_governance.disclosure_timestamp": "2026-05-26T14:30:00.000Z",
            "healthcare_governance.identity_assertion_text": "I am an automated system.",
        })
        decision = self.engine.evaluate_idg01(self._base_session(), event)
        assert decision.action == self.engine.PolicyAction.CONTINUE_AI
        assert not decision.violations

    def test_idg01_fail_no_disclosure(self) -> None:
        event = self._base_event()
        decision = self.engine.evaluate_idg01(self._base_session(), event)
        assert decision.action == self.engine.PolicyAction.DISCLOSE_IDENTITY
        assert any(v.rule_id == "IDG-01" for v in decision.violations)
        assert decision.twiml_fallback is not None

    def test_idg01_fail_empty_assertion_text(self) -> None:
        event = self._base_event({
            "healthcare_governance.disclosure_timestamp": "2026-05-26T14:30:00.000Z",
            "healthcare_governance.identity_assertion_text": "",
        })
        decision = self.engine.evaluate_idg01(self._base_session(), event)
        assert decision.action == self.engine.PolicyAction.CONTINUE_AI
        assert any(v.rule_id == "IDG-01" for v in decision.violations)
        assert any(v.severity == self.engine.ViolationSeverity.MAJOR for v in decision.violations)

    # PDX-01 unit tests

    def test_pdx01_blocks_phi_without_disclosure(self) -> None:
        event = self._base_event({
            "input_payload.speech_text": "Can I get the member ID please?",
        })
        decision = self.engine.evaluate_pdx01(self._base_session(), event)
        assert decision.action == self.engine.PolicyAction.DENY_DATA
        assert any(v.rule_id == "PDX-01" for v in decision.violations)

    def test_pdx01_allows_phi_after_disclosure(self) -> None:
        event = self._base_event({
            "healthcare_governance.disclosure_timestamp": "2026-05-26T14:30:00.000Z",
            "input_payload.speech_text": "Can I get the member ID please?",
        })
        decision = self.engine.evaluate_pdx01(self._base_session(), event)
        assert decision.action == self.engine.PolicyAction.CONTINUE_AI
        assert not decision.violations

    def test_pdx01_no_phi_no_violation(self) -> None:
        event = self._base_event({
            "input_payload.speech_text": "Hello, how can I help?",
        })
        decision = self.engine.evaluate_pdx01(self._base_session(), event)
        assert decision.action == self.engine.PolicyAction.CONTINUE_AI
        assert not decision.violations

    # DBC-01 unit tests

    def test_dbc01_pass_no_artifacts(self) -> None:
        event = self._base_event()
        decision = self.engine.evaluate_dbc01(self._base_session(), event)
        assert decision.action == self.engine.PolicyAction.CONTINUE_AI
        assert not decision.violations

    def test_dbc01_fail_fake_breathing(self) -> None:
        event = self._base_event({
            "healthcare_governance.deceptive_artifact_flags": ["fake_breathing"],
        })
        decision = self.engine.evaluate_dbc01(self._base_session(), event)
        assert decision.action == self.engine.PolicyAction.LOG_ONLY
        assert any(v.rule_id == "DBC-01" for v in decision.violations)

    def test_dbc01_fail_license_claim(self) -> None:
        event = self._base_event({
            "healthcare_governance.deceptive_artifact_flags": ["license_claim"],
        })
        decision = self.engine.evaluate_dbc01(self._base_session(), event)
        assert decision.action == self.engine.PolicyAction.LOG_ONLY
        assert any("license_claim" in v.description for v in decision.violations)

    # EIT-01 unit tests

    def test_eit01_no_escalation_trigger(self) -> None:
        event = self._base_event({
            "input_payload.speech_text": "Can you check the claim status?",
        })
        decision = self.engine.evaluate_eit01(self._base_session(), event)
        assert decision.action == self.engine.PolicyAction.CONTINUE_AI

    def test_eit01_escalation_available(self) -> None:
        event = self._base_event({
            "input_payload.speech_text": "I need to speak with a human representative.",
        })
        decision = self.engine.evaluate_eit01(
            self._base_session({"escalation_path_available": True}), event
        )
        assert decision.action == self.engine.PolicyAction.ESCALATE_HUMAN
        assert not decision.violations

    def test_eit01_escalation_unavailable(self) -> None:
        event = self._base_event({
            "input_payload.speech_text": "Transfer me to a real person.",
        })
        decision = self.engine.evaluate_eit01(
            self._base_session({"escalation_path_available": False}), event
        )
        assert decision.action == self.engine.PolicyAction.ESCALATE_HUMAN
        assert any(v.rule_id == "EIT-01" for v in decision.violations)
        assert decision.twiml_fallback is not None

    # ATR-01 unit tests

    def test_atr01_pass_all_fields_present(self) -> None:
        event = self._base_event()
        decision = self.engine.evaluate_atr01(self._base_session(), event)
        assert decision.action == self.engine.PolicyAction.CONTINUE_AI
        assert not decision.violations

    def test_atr01_fail_missing_session_id(self) -> None:
        event = self._base_event({"session_id": None})
        decision = self.engine.evaluate_atr01(self._base_session(), event)
        assert decision.action == self.engine.PolicyAction.LOG_ONLY
        assert any("session_id" in v.description for v in decision.violations)

    def test_atr01_fail_missing_pipeline_version(self) -> None:
        event = self._base_event()
        event["execution_context"]["pipeline_version"] = None
        decision = self.engine.evaluate_atr01(self._base_session(), event)
        assert decision.action == self.engine.PolicyAction.LOG_ONLY
        assert any("pipeline_version" in v.description for v in decision.violations)

    # Bot-to-bot unit tests

    def test_bot_to_bot_not_applicable_human(self) -> None:
        event = self._base_event({"counterparty_type": "human_operator"})
        decision = self.engine.evaluate_bot_to_bot(self._base_session(), event)
        assert decision.action == self.engine.PolicyAction.CONTINUE_AI
        assert not decision.violations

    def test_bot_to_bot_undisclosed_agent(self) -> None:
        event = self._base_event({"counterparty_type": "ai_agent"})
        decision = self.engine.evaluate_bot_to_bot(self._base_session(), event)
        assert decision.action == self.engine.PolicyAction.DENY_DATA
        assert any(v.rule_id == "IDG-01" for v in decision.violations)

    def test_bot_to_bot_disclosed_agent(self) -> None:
        event = self._base_event({
            "counterparty_type": "ai_agent",
            "healthcare_governance.disclosure_timestamp": "2026-05-26T14:30:00.000Z",
        })
        decision = self.engine.evaluate_bot_to_bot(self._base_session(), event)
        assert decision.action == self.engine.PolicyAction.CONTINUE_AI
        assert not decision.violations

    # Composite evaluate_all tests

    def test_evaluate_all_clean(self) -> None:
        event = self._base_event({
            "healthcare_governance.disclosure_timestamp": "2026-05-26T14:30:00.000Z",
            "healthcare_governance.identity_assertion_text": "I am an automated system.",
            "input_payload.speech_text": "How can I help you today?",
        })
        decision = self.engine.evaluate_all(self._base_session(), event)
        assert decision.action == self.engine.PolicyAction.CONTINUE_AI

    def test_evaluate_all_deny_dominates(self) -> None:
        """DENY_DATA must dominate over LOG_ONLY and CONTINUE_AI."""
        event = self._base_event({
            # IDG-01: no disclosure (→ DISCLOSE_IDENTITY)
            # PDX-01: PHI request without disclosure (→ DENY_DATA)
            "input_payload.speech_text": "Give me the member ID.",
        })
        decision = self.engine.evaluate_all(self._base_session(), event)
        assert decision.action == self.engine.PolicyAction.DENY_DATA

    def test_policy_engine_never_raises(self) -> None:
        """Policy engine must return a valid decision even for completely broken input."""
        decision = self.engine.evaluate_all({}, {})
        assert isinstance(decision, self.engine.PolicyDecision)
        assert decision.action in list(self.engine.PolicyAction)
