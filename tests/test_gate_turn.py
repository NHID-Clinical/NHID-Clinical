"""POST /v1/gate/turn: the pre-utterance gate for an agent that places the call.

Why this route exists
---------------------
The call-progress webhook runs PHI detection only on ``speaker == "user"``
turns. It was written receiver-side, where the human asks and the agent
discloses. An agent that is the CALLER is the one asking, so labelling its
turns honestly as ``agent`` meant PDX-01 never saw the data request. Proved on
the live API: the same words came back ``DISCLOSE_IDENTITY`` as an agent turn
and ``DENY_DATA / PDX01_PHI_GATE_TRIGGERED`` as a user turn.

The gate takes what the agent is about to say and runs it through the same
detection a human's turn gets. The first test below is the one that fails
against the webhook route and passes here; it is the reason for the file.

The decision is ``evaluate_all``'s. These tests assert the reshaping around
it and never restate control semantics.
"""
import json
import os
import sys
from urllib.parse import parse_qsl

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from functions.demo_scripts import COMPLIANT_SCRIPT  # noqa: E402
from functions.handler import lambda_handler  # noqa: E402

ROUTE = "/v1/gate/turn"
PHI_REQUEST = "Great, thanks. Can I get the member ID and date of birth for the claim?"
DISCLOSURE = COMPLIANT_SCRIPT[0]["text"]


def _gate(query: str | None = None, body=None, method: str = "POST") -> tuple[int, dict]:
    event = {"httpMethod": method, "path": ROUTE}
    if query is not None:
        event["queryStringParameters"] = dict(parse_qsl(query, keep_blank_values=True))
    if body is not None:
        event["body"] = body if isinstance(body, str) else json.dumps(body)
    response = lambda_handler(event, None)
    return response["statusCode"], json.loads(response["body"])


# ── The orientation fix ──────────────────────────────────────────────────────

def test_an_undisclosed_agent_asking_for_phi_is_denied():
    """The case the webhook route under-enforces. The agent is the caller; its
    own planned words are the data request."""
    status, out = _gate(f"session_id=t1&turn={PHI_REQUEST}&disclosed=false")
    assert status == 200
    assert out["allowed"] is False
    assert out["action"] == "DENY_DATA"
    assert out["reason_code"] == "PDX01_PHI_GATE_TRIGGERED"
    assert "member_id" in out["phi_requested"]  # the engine's field name, not the adapter's phrase


def test_the_webhook_route_would_have_let_the_same_turn_through():
    """Documents the gap the gate closes. If the webhook ever starts catching
    agent-side requests, this test fails and the gate's docstring is stale."""
    response = lambda_handler({
        "httpMethod": "POST", "path": "/v1/webhooks/call-progress",
        "body": json.dumps({
            "session_id": "t1", "turn_index": 0, "speaker": "agent", "text": PHI_REQUEST,
            "session_state": {"turn_count": 1, "disclosure_timestamp": None, "escalation_available": True},
        }),
    }, None)
    out = json.loads(response["body"])
    assert out["reason_code"] != "PDX01_PHI_GATE_TRIGGERED", (
        "the webhook route now catches agent-side PHI requests; update the gate's rationale"
    )


def test_after_disclosure_the_same_request_is_allowed():
    status, out = _gate(f"session_id=t1&turn={PHI_REQUEST}&disclosed=true&turn_index=2")
    assert status == 200
    assert out["allowed"] is True, out
    assert out["reason_code"] != "PDX01_PHI_GATE_TRIGGERED"
    assert out["say_instead"] is None


def test_disclosing_and_asking_in_the_same_breath_is_still_denied():
    """Same-turn disclosure plus a request fails PDX-01. The engine's rule;
    the gate must not soften it by treating this turn's disclosure as prior."""
    status, out = _gate(f"session_id=t1&turn={DISCLOSURE} {PHI_REQUEST}&disclosed=false")
    assert status == 200
    assert out["allowed"] is False
    assert out["action"] == "DENY_DATA"


def test_an_undisclosed_agent_saying_nothing_protected_is_told_to_disclose():
    status, out = _gate("session_id=t1&turn=Am I speaking with the claims department?&disclosed=false")
    assert status == 200
    assert out["allowed"] is False
    assert out["action"] == "DISCLOSE_IDENTITY"
    assert out["say_instead"] == DISCLOSURE


def test_a_disclosing_turn_is_allowed():
    """The agent's own disclosure sentence passes: this is the turn the gate
    wants it to say."""
    status, out = _gate(f"session_id=t1&turn={DISCLOSURE}&disclosed=false")
    assert status == 200
    assert out["allowed"] is True, out


def test_the_other_party_asking_for_a_human_returns_escalate_human():
    """EIT-01 reads the request from the counterparty's words, so the gate
    carries them in `heard` rather than taking a bare flag on trust."""
    status, out = _gate("session_id=t1&turn=Let me check the status for you.&disclosed=true"
                        "&heard=Can I speak to a real person please?")
    assert status == 200
    assert out["action"] == "ESCALATE_HUMAN"
    assert out["reason_code"] == "EIT01_ESCALATION_TRIGGERED"
    assert out["allowed"] is False
    assert "Transfer" in out["instruction"]


def test_protected_data_volunteered_before_disclosure_is_denied():
    """The receiver-side case still works through `heard`: the other party
    reads out a member ID before the agent has disclosed."""
    status, out = _gate("session_id=t1&turn=Thank you.&disclosed=false"
                        "&heard=Sure, the member ID is 87654321.")
    assert status == 200
    assert out["action"] == "DENY_DATA"
    assert out["reason_code"] == "PDX01_PHI_GATE_TRIGGERED"


def test_a_human_claim_in_the_agents_own_words_is_a_dbc01_finding():
    """DBC-01 judges the agent's identity assertion. The gate hands it the
    planned turn, so 'I'm a nurse' is caught before it is said."""
    status, out = _gate("session_id=t1&turn=Hi, this is Sarah, I'm a nurse at Dr. Smith's office.&disclosed=true&turn_index=1")
    assert status == 200
    assert any(v["rule_id"] == "DBC-01" for v in out["violations"]), out


# ── The response the agent acts on ───────────────────────────────────────────

def test_say_instead_is_the_repository_disclosure_line():
    """One source for the disclosure wording. Reword COMPLIANT_SCRIPT[0] and
    the agent's fallback moves with it; drift between them fails here."""
    _, out = _gate(f"session_id=t1&turn={PHI_REQUEST}&disclosed=false")
    assert out["say_instead"] == COMPLIANT_SCRIPT[0]["text"]
    assert "automated AI assistant" in out["say_instead"]


def test_every_action_has_an_instruction_and_allowed_follows_the_ladder():
    from functions.handler import _GATE_INSTRUCTION
    assert set(_GATE_INSTRUCTION) == {"DENY_DATA", "ESCALATE_HUMAN", "DISCLOSE_IDENTITY", "LOG_ONLY", "CONTINUE_AI"}
    # allowed is derived from the action, nothing else
    for query, expect in (
        (f"session_id=t1&turn={PHI_REQUEST}&disclosed=false", False),
        (f"session_id=t1&turn={PHI_REQUEST}&disclosed=true&turn_index=1", True),
    ):
        _, out = _gate(query)
        assert out["allowed"] is expect
        assert out["allowed"] == (out["action"] in ("CONTINUE_AI", "LOG_ONLY"))


def test_the_response_carries_the_engine_fields_unchanged():
    """The gate adds fields; it does not rename or drop the engine's."""
    _, out = _gate(f"session_id=t1&turn={PHI_REQUEST}&disclosed=false")
    for key in ("action", "reason_code", "policy_version", "violations", "next_state",
                "evidence_completeness", "human_review"):
        assert key in out, key
    assert {v["rule_id"] for v in out["violations"]} >= {"IDG-01", "PDX-01"}


def test_a_json_body_with_the_same_keys_works_too():
    status, out = _gate(body={"session_id": "t1", "turn": PHI_REQUEST, "disclosed": "false"})
    assert status == 200
    assert out["action"] == "DENY_DATA"


# ── Input hardening: a status code, never a traceback ────────────────────────

@pytest.mark.parametrize("query, fragment", [
    ("turn=hello&disclosed=false", "session_id"),
    ("session_id=t1&disclosed=false", "turn is required"),
    ("session_id=t1&turn=hello&disclosed=maybe", "disclosed must be true or false"),
    ("session_id=t1&turn=hello&turn_index=abc", "Invalid gate parameters"),
    ("session_id=t1&turn=hello&turn_index=-1", "turn_index"),
])
def test_bad_parameters_get_a_400_with_a_reason(query, fragment):
    status, out = _gate(query)
    assert status == 400
    assert fragment in out["error"]


def test_an_overlong_turn_is_refused():
    status, out = _gate(f"session_id=t1&turn={'x' * 4001}&disclosed=false")
    assert status == 400
    assert "4000" in out["error"]


def test_an_overlong_heard_is_refused():
    status, out = _gate(f"session_id=t1&turn=hello&heard={'x' * 4001}")
    assert status == 400
    assert "heard" in out["error"]


def test_a_deeply_nested_body_is_refused_not_crashed():
    status, out = _gate(body='{"a":' * 5000 + "null" + "}" * 5000)
    assert status == 400
    assert "Invalid JSON" in out["error"]


def test_no_parameters_at_all_is_a_400():
    status, out = _gate()
    assert status == 400


# ── The route is wired everywhere it needs to be ─────────────────────────────

def test_the_route_is_declared_in_the_sam_template_and_the_handler_docstring():
    root = os.path.join(os.path.dirname(__file__), "..")
    with open(os.path.join(root, "template.yaml"), encoding="utf-8") as fh:
        assert "Path: /v1/gate/turn" in fh.read(), "template.yaml does not expose /v1/gate/turn"
    assert ROUTE in (lambda_handler.__doc__ or ""), "the handler's route list omits /v1/gate/turn"
