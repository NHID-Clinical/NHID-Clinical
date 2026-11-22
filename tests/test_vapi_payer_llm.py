"""The payer's AI live on Vapi: the gate on every caller turn.

docs/agent-to-agent-calls.md, "Live on Vapi". The canonical direction holds:
the caller-agent places the call and asks for a claim status; the payer's AI
answers through `POST /v1/vapi/payer-llm/chat/completions`, Vapi's "Custom
LLM" for that assistant, and says only what the gate allows.

What these tests pin:
  * every scenario ends the same way over the Vapi route as in the offline
    `run_call`, line for line, because both run `agent_to_agent.take_turn`;
  * the route speaks the OpenAI chat-completions wire format Vapi expects;
  * the shared secret is enforced, and a strict deployment with no secret
    refuses rather than serving;
  * calls do not share state, and a resent turn is not gated twice;
  * the after-call record judges the CALLER, never the payer's AI.
"""
from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient  # noqa: E402

import app as voice_app  # noqa: E402
from src import agent_to_agent as a2a  # noqa: E402
from src import vapi_payer_llm as payer_llm  # noqa: E402

ROUTE = "/v1/vapi/payer-llm/chat/completions"


@pytest.fixture(autouse=True)
def _fresh(monkeypatch):
    monkeypatch.delenv(payer_llm.SECRET_ENV, raising=False)
    monkeypatch.delenv("DEPLOYMENT_MODE", raising=False)
    monkeypatch.setattr(payer_llm, "CALLS", payer_llm.CallBook())


@pytest.fixture
def client():
    return TestClient(voice_app.app)


def vapi_body(call_id, caller_lines, payer_lines, *, stream=True):
    """What Vapi sends: the conversation so far, the newest caller line last."""
    messages = [{"role": "system", "content": "You are the payer's assistant."}]
    for i, line in enumerate(caller_lines):
        messages.append({"role": "assistant", "content": payer_lines[i]})
        messages.append({"role": "user", "content": line})
    return {"model": "nhid-payer-reference", "stream": stream, "messages": messages,
            "call": {"id": call_id}}


def spoken(response) -> str:
    """The text of an SSE answer, joined from its content deltas."""
    text = ""
    for line in response.text.splitlines():
        if line.startswith("data: ") and line != "data: [DONE]":
            for choice in json.loads(line[6:])["choices"]:
                text += choice["delta"].get("content", "")
    return text


def drive(client, call_id, caller_turns):
    """Play a whole call through the route, as Vapi would, turn by turn."""
    payer = [a2a.PayerAgent().greeting()]
    for n in range(1, len(caller_turns) + 1):
        r = client.post(ROUTE, json=vapi_body(call_id, caller_turns[:n], payer))
        assert r.status_code == 200, r.text
        payer.append(spoken(r))
        if payer[-1] == a2a.PayerAgent.LINES["transfer"]:
            break
    return payer


# ── same rules live as offline ──────────────────────────────────────────────

@pytest.mark.parametrize("name", sorted(a2a.SCENARIOS))
def test_every_scenario_ends_the_same_way_live_as_offline(client, name):
    scenario = a2a.SCENARIOS[name]
    offline = a2a.run_call(scenario, signer=None)
    live = drive(client, f"live-{name}", list(scenario.caller_turns))
    assert live == [t.text for t in offline.turns if t.speaker == "payer_agent"]
    state = payer_llm.CALLS.get(f"live-{name}", a2a.PayerAgent())
    assert a2a.outcome_of(state) == offline.outcome


def test_a_disclosed_caller_with_no_delegation_hears_no_member_data(client):
    """Phase 1 on Vapi: Ida discloses but carries no delegation. Disclosure is
    not authorization, so the payer's AI refuses."""
    lines = drive(client, "live-phase-1", [a2a.DISCLOSE, a2a.ASK])
    assert lines[-1] == a2a.PayerAgent.LINES["no_delegation"]
    assert "9921-0417" not in " ".join(lines[1:])


def test_the_gate_sees_an_ai_on_the_other_end():
    status, result = payer_llm.answer(vapi_body("cp-1", [a2a.ASK], [a2a.PayerAgent().greeting()]))
    assert status == 200
    assert result["gate"]["counterparty"] == "ai_agent"
    assert result["gate"]["allowed"] is False


# ── wire format ─────────────────────────────────────────────────────────────

def test_the_answer_streams_as_openai_chat_completion_chunks(client):
    r = client.post(ROUTE, json=vapi_body("wire-1", [a2a.DISCLOSE], ["hi"]))
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")
    events = [line for line in r.text.splitlines() if line]
    assert all(e.startswith("data: ") for e in events)
    assert events[-1] == "data: [DONE]"
    first, last = json.loads(events[0][6:]), json.loads(events[-2][6:])
    assert first["object"] == "chat.completion.chunk"
    assert first["choices"][0]["delta"]["content"] == a2a.PayerAgent.LINES["go_ahead"]
    assert last["choices"][0]["finish_reason"] == "stop"


def test_a_non_streaming_request_gets_one_completion(client):
    r = client.post(ROUTE, json=vapi_body("wire-2", [a2a.DISCLOSE], ["hi"], stream=False))
    body = r.json()
    assert body["object"] == "chat.completion"
    assert body["choices"][0]["message"]["content"] == a2a.PayerAgent.LINES["go_ahead"]


def test_before_the_caller_speaks_the_payer_ai_says_it_is_automated(client):
    r = client.post(ROUTE, json={"messages": [], "call": {"id": "wire-3"}, "stream": False})
    assert "automated" in r.json()["choices"][0]["message"]["content"]


@pytest.mark.parametrize("body,code", [
    ({"messages": []}, 400),                                    # no call id
    ({"messages": [], "call": {"id": "x" * 201}}, 400),         # call id too long
    ({"messages": [{"role": "user", "content": "a" * 2001}], "call": {"id": "c"}}, 400),
])
def test_bad_requests_are_refused(client, body, code):
    assert client.post(ROUTE, json=body).status_code == code


def test_a_body_that_is_not_json_is_refused(client):
    assert client.post(ROUTE, content=b"not json",
                       headers={"content-type": "application/json"}).status_code == 400


# ── the shared secret ───────────────────────────────────────────────────────

def test_the_secret_is_required_once_configured(client, monkeypatch):
    monkeypatch.setenv(payer_llm.SECRET_ENV, "s3cret-for-tests")
    body = vapi_body("auth-1", [a2a.DISCLOSE], ["hi"])
    assert client.post(ROUTE, json=body).status_code == 401
    assert client.post(ROUTE, json=body, headers={"X-Vapi-Secret": "wrong"}).status_code == 401
    assert client.post(ROUTE, json=body, headers={"X-Vapi-Secret": "s3cret-for-tests"}).status_code == 200
    assert client.post(ROUTE, json=body,
                       headers={"Authorization": "Bearer s3cret-for-tests"}).status_code == 200


@pytest.mark.parametrize("mode", ["staging", "production"])
def test_a_strict_deployment_without_a_secret_refuses(client, monkeypatch, mode):
    monkeypatch.setenv("DEPLOYMENT_MODE", mode)
    r = client.post(ROUTE, json=vapi_body("auth-2", [a2a.DISCLOSE], ["hi"]))
    assert r.status_code == 503
    assert payer_llm.SECRET_ENV in r.json()["detail"]


# ── state ───────────────────────────────────────────────────────────────────

def test_calls_do_not_share_state(client):
    greeting = a2a.PayerAgent().greeting()
    # Call A refuses on its first turn; call B, interleaved, is unaffected.
    client.post(ROUTE, json=vapi_body("iso-A", [a2a.ASK], [greeting]))
    r = client.post(ROUTE, json=vapi_body("iso-B", [a2a.DISCLOSE], [greeting]))
    assert spoken(r) == a2a.PayerAgent.LINES["go_ahead"]
    book = payer_llm.CALLS
    assert book.get("iso-A", a2a.PayerAgent()).refused is True
    assert book.get("iso-B", a2a.PayerAgent()).refused is False


def test_a_resent_turn_is_not_gated_twice():
    calls = []

    def counting_gate(params):
        calls.append(params["turn"])
        from functions import handler
        return handler.gate_turn(params)

    body = vapi_body("resend-1", [a2a.DISCLOSE], ["hi"])
    first = payer_llm.answer(body, gate_fn=counting_gate)
    again = payer_llm.answer(body, gate_fn=counting_gate)
    assert calls == [a2a.DISCLOSE]
    assert first[1]["text"] == again[1]["text"]


def test_the_call_book_forgets_the_oldest_call_first():
    book = payer_llm.CallBook(limit=2)
    agent = a2a.PayerAgent()
    for cid in ("one", "two", "three"):
        book.get(cid, agent).turn_index = 7
    assert book.get("one", agent).turn_index == 0     # dropped, so it starts fresh
    assert book.get("three", agent).turn_index == 7


# ── after the call: the CALLER is judged ────────────────────────────────────

def report(messages, call_id="eoc-1"):
    return {"message": {"type": "end-of-call-report", "call": {"id": call_id},
                        "artifact": {"messages": messages}}}


def test_the_end_of_call_report_becomes_an_nhid_record(client):
    messages = [
        {"role": "system", "message": "prompt, never spoken"},
        {"role": "bot", "message": a2a.DISCLOSE, "secondsFromStart": 0.4},
        {"role": "user", "message": "Go ahead.", "secondsFromStart": 3.0},
        {"role": "bot", "message": a2a.ASK, "secondsFromStart": 4.1},
        {"role": "user", "message": a2a.PayerAgent.LINES["no_delegation"], "secondsFromStart": 8.0},
    ]
    r = client.post("/v1/vapi/events", json=report(messages))
    assert r.status_code == 200, r.text
    trace = r.json()["nhid_trace"]
    texts = json.dumps(trace)
    assert "prompt, never spoken" not in texts
    assert a2a.DISCLOSE in texts


def test_other_vapi_messages_are_acknowledged_and_ignored(client):
    r = client.post("/v1/vapi/events", json={"message": {"type": "status-update"}})
    assert r.json() == {"ignored": "status-update"}


def test_the_record_is_saved_when_an_evidence_folder_is_set(client, monkeypatch, tmp_path):
    monkeypatch.setenv("NHID_VAPI_EVIDENCE_DIR", str(tmp_path))
    client.post("/v1/vapi/events", json=report(
        [{"role": "bot", "message": a2a.DISCLOSE, "secondsFromStart": 0.2}], call_id="eoc-save-1"))
    saved = json.loads((tmp_path / "eoc-save-1.json").read_text())
    assert saved["vapi_messages"][0]["message"] == a2a.DISCLOSE


def test_an_unsafe_call_id_is_never_used_as_a_file_name(client, monkeypatch, tmp_path):
    monkeypatch.setenv("NHID_VAPI_EVIDENCE_DIR", str(tmp_path))
    client.post("/v1/vapi/events", json=report([], call_id="../../escape"))
    assert list(tmp_path.iterdir()) == []


def test_the_events_route_needs_the_secret_too(client, monkeypatch):
    monkeypatch.setenv(payer_llm.SECRET_ENV, "s3cret-for-tests")
    assert client.post("/v1/vapi/events", json=report([])).status_code == 401


def test_the_deployed_app_serves_both_routes_under_voice():
    import main
    mounted = next(r for r in main.app.routes if getattr(r, "path", "") == "/voice")
    paths = {getattr(r, "path", "") for r in mounted.app.routes}
    assert {ROUTE, "/v1/vapi/events"} <= paths


# ── the Vapi setup script ───────────────────────────────────────────────────

def test_the_setup_script_builds_the_two_assistants_the_right_way_round():
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
    import vapi_setup

    ida = vapi_setup.ida_assistant("https://api.example.org", "gpt-4o-mini")
    payer = vapi_setup.payer_assistant("https://api.example.org/")
    # Ida places the call, discloses first, and is the one audited after it.
    assert ida["firstMessage"] == a2a.DISCLOSE
    assert a2a.DISCLOSE in ida["model"]["messages"][0]["content"]
    assert ida["server"]["url"] == "https://api.example.org/voice/v1/vapi/events"
    assert ida["serverMessages"] == ["end-of-call-report"]
    # The payer's AI answers first, speaks only what the gate route returns,
    # and its own call record is never audited as if it were the caller.
    assert payer["firstMessageMode"] == "assistant-speaks-first"
    assert payer["model"]["provider"] == "custom-llm"
    assert payer["model"]["url"] == "https://api.example.org/voice/v1/vapi/payer-llm"
    assert payer["serverMessages"] == []


def test_the_setup_script_refuses_plain_http():
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
    import vapi_setup
    assert vapi_setup.main(["--public-url", "http://api.example.org", "--dry-run"]) == 2
